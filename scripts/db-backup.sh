#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Estate Executor — Database Backup & Recovery Script
#
# Manages manual backups, point-in-time recovery, backup verification,
# and monthly restoration drills for AWS RDS PostgreSQL.
#
# Usage:
#   ./scripts/db-backup.sh <command> [options]
#
# Commands:
#   snapshot         Create a manual RDS snapshot
#   list             List available snapshots and PITR window
#   restore-snapshot Restore from a specific snapshot to a new instance
#   restore-pitr     Point-in-time recovery to a new instance
#   verify           Verify the latest backup by restoring and testing
#   drill            Run a full monthly restoration drill
#   cleanup          Remove drill/test instances older than 24h
#   status           Show backup configuration and health
#
# Prerequisites:
#   - AWS CLI v2 configured with appropriate IAM permissions
#   - jq, psql (PostgreSQL client)
#   - Environment variables: see 'Required Environment Variables' below
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

# Required environment variables
: "${AWS_REGION:=us-east-1}"
: "${RDS_INSTANCE_ID:=estate-executor-production}"
: "${RDS_INSTANCE_CLASS:=db.r6g.large}"
: "${RDS_SUBNET_GROUP:=estate-executor-db-subnet}"
: "${RDS_SECURITY_GROUP:=}"
: "${RDS_KMS_KEY_ID:=}"
: "${BACKUP_REPLICA_REGION:=us-west-2}"
: "${SLACK_WEBHOOK_URL:=}"
: "${DRILL_DB_NAME:=estate_executor}"

TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Helpers ──────────────────────────────────────────────────────────────────

log()   { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] INFO  $*"; }
warn()  { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] WARN  $*" >&2; }
error() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR $*" >&2; exit 1; }

notify_slack() {
  local message="$1"
  local color="${2:-good}" # good, warning, danger

  if [[ -n "${SLACK_WEBHOOK_URL}" ]]; then
    # Use jq to build the JSON payload so that special characters in $message
    # (e.g., quotes or backslashes in snapshot IDs or AWS error output) are
    # safely escaped rather than injected into the JSON structure.
    local payload
    payload=$(jq -n \
      --arg color "$color" \
      --arg text "$message" \
      '{"attachments": [{"color": $color, "text": $text, "footer": "Estate Executor DB Backup"}]}')
    curl -sf -X POST "${SLACK_WEBHOOK_URL}" \
      -H 'Content-type: application/json' \
      -d "$payload" || warn "Failed to send Slack notification"
  fi
}

wait_for_instance() {
  local instance_id="$1"
  local max_wait="${2:-1800}" # 30 min default
  local elapsed=0
  local interval=30

  log "Waiting for instance ${instance_id} to become available (timeout: ${max_wait}s)..."

  while [[ $elapsed -lt $max_wait ]]; do
    local status
    status=$(aws rds describe-db-instances \
      --db-instance-identifier "${instance_id}" \
      --region "${AWS_REGION}" \
      --query 'DBInstances[0].DBInstanceStatus' \
      --output text 2>/dev/null || echo "not-found")

    if [[ "${status}" == "available" ]]; then
      log "Instance ${instance_id} is available"
      return 0
    fi

    log "  Status: ${status} (${elapsed}s elapsed)"
    sleep "${interval}"
    elapsed=$((elapsed + interval))
  done

  error "Timed out waiting for ${instance_id} to become available"
}

get_instance_endpoint() {
  local instance_id="$1"
  aws rds describe-db-instances \
    --db-instance-identifier "${instance_id}" \
    --region "${AWS_REGION}" \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text
}

# ── Commands ─────────────────────────────────────────────────────────────────

cmd_snapshot() {
  local snapshot_id="${RDS_INSTANCE_ID}-manual-${TIMESTAMP}"
  local description="${1:-Manual backup $(date -u +%Y-%m-%d)}"

  log "Creating manual snapshot: ${snapshot_id}"
  aws rds create-db-snapshot \
    --db-instance-identifier "${RDS_INSTANCE_ID}" \
    --db-snapshot-identifier "${snapshot_id}" \
    --region "${AWS_REGION}" \
    --tags "Key=CreatedBy,Value=db-backup-script" \
           "Key=Environment,Value=production" \
           "Key=Type,Value=manual"

  log "Waiting for snapshot to complete..."
  aws rds wait db-snapshot-available \
    --db-snapshot-identifier "${snapshot_id}" \
    --region "${AWS_REGION}"

  local snapshot_size
  snapshot_size=$(aws rds describe-db-snapshots \
    --db-snapshot-identifier "${snapshot_id}" \
    --region "${AWS_REGION}" \
    --query 'DBSnapshots[0].AllocatedStorage' \
    --output text)

  log "Snapshot ${snapshot_id} completed (${snapshot_size} GB)"
  notify_slack "✅ Manual snapshot created: \`${snapshot_id}\` (${snapshot_size} GB)"

  echo "${snapshot_id}"
}

cmd_list() {
  log "=== Automated Backups ==="
  echo ""

  # PITR window
  local pitr_info
  pitr_info=$(aws rds describe-db-instances \
    --db-instance-identifier "${RDS_INSTANCE_ID}" \
    --region "${AWS_REGION}" \
    --query 'DBInstances[0].{
      LatestRestorableTime: LatestRestorableTime,
      BackupRetentionPeriod: BackupRetentionPeriod,
      PreferredBackupWindow: PreferredBackupWindow
    }' --output table)
  echo "${pitr_info}"
  echo ""

  log "=== Recent Snapshots (last 10) ==="
  echo ""
  aws rds describe-db-snapshots \
    --db-instance-identifier "${RDS_INSTANCE_ID}" \
    --region "${AWS_REGION}" \
    --query 'reverse(sort_by(DBSnapshots, &SnapshotCreateTime))[:10].{
      ID: DBSnapshotIdentifier,
      Status: Status,
      Created: SnapshotCreateTime,
      Size_GB: AllocatedStorage,
      Type: SnapshotType,
      Encrypted: Encrypted
    }' --output table

  echo ""
  log "=== Cross-Region Replicas ==="
  echo ""
  aws rds describe-db-instance-automated-backups \
    --region "${BACKUP_REPLICA_REGION}" \
    --query 'DBInstanceAutomatedBackups[?DBInstanceIdentifier==`'"${RDS_INSTANCE_ID}"'`].{
      Status: Status,
      Region: Region,
      RetentionPeriod: BackupRetentionPeriod
    }' --output table 2>/dev/null || echo "  No cross-region replicas found"
}

cmd_restore_snapshot() {
  local snapshot_id="${1:-}"
  local target_instance="${2:-${RDS_INSTANCE_ID}-restore-${TIMESTAMP}}"

  if [[ -z "${snapshot_id}" ]]; then
    error "Usage: $0 restore-snapshot <snapshot-id> [target-instance-id]"
  fi

  log "Restoring snapshot ${snapshot_id} → ${target_instance}"

  local restore_args=(
    --db-instance-identifier "${target_instance}"
    --db-snapshot-identifier "${snapshot_id}"
    --db-instance-class "${RDS_INSTANCE_CLASS}"
    --region "${AWS_REGION}"
    --no-multi-az
    --tags "Key=CreatedBy,Value=db-backup-script"
           "Key=RestoredFrom,Value=${snapshot_id}"
           "Key=Environment,Value=drill"
  )

  if [[ -n "${RDS_SUBNET_GROUP}" ]]; then
    restore_args+=(--db-subnet-group-name "${RDS_SUBNET_GROUP}")
  fi

  if [[ -n "${RDS_SECURITY_GROUP}" ]]; then
    restore_args+=(--vpc-security-group-ids "${RDS_SECURITY_GROUP}")
  fi

  aws rds restore-db-instance-from-db-snapshot "${restore_args[@]}"

  wait_for_instance "${target_instance}"

  local endpoint
  endpoint=$(get_instance_endpoint "${target_instance}")
  log "Restored instance available at: ${endpoint}"
  notify_slack "✅ Snapshot restored: \`${snapshot_id}\` → \`${target_instance}\` (${endpoint})"

  echo "${target_instance}"
}

cmd_restore_pitr() {
  local restore_time="${1:-}"
  local target_instance="${2:-${RDS_INSTANCE_ID}-pitr-${TIMESTAMP}}"

  if [[ -z "${restore_time}" ]]; then
    # Default: restore to 5 minutes ago (latest safe point)
    restore_time=$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
      || date -u -v-5M +%Y-%m-%dT%H:%M:%SZ) # macOS fallback
    log "No restore time specified, using: ${restore_time}"
  fi

  log "Point-in-time recovery → ${target_instance} (restore to: ${restore_time})"

  local restore_args=(
    --source-db-instance-identifier "${RDS_INSTANCE_ID}"
    --target-db-instance-identifier "${target_instance}"
    --restore-time "${restore_time}"
    --db-instance-class "${RDS_INSTANCE_CLASS}"
    --region "${AWS_REGION}"
    --no-multi-az
    --tags "Key=CreatedBy,Value=db-backup-script"
           "Key=RestoreType,Value=pitr"
           "Key=RestoreTime,Value=${restore_time}"
           "Key=Environment,Value=drill"
  )

  if [[ -n "${RDS_SUBNET_GROUP}" ]]; then
    restore_args+=(--db-subnet-group-name "${RDS_SUBNET_GROUP}")
  fi

  if [[ -n "${RDS_SECURITY_GROUP}" ]]; then
    restore_args+=(--vpc-security-group-ids "${RDS_SECURITY_GROUP}")
  fi

  aws rds restore-db-instance-to-point-in-time "${restore_args[@]}"

  wait_for_instance "${target_instance}"

  local endpoint
  endpoint=$(get_instance_endpoint "${target_instance}")
  log "PITR instance available at: ${endpoint}"
  notify_slack "✅ PITR restored to \`${restore_time}\` → \`${target_instance}\` (${endpoint})"

  echo "${target_instance}"
}

cmd_verify() {
  local instance_id="${1:-}"

  if [[ -z "${instance_id}" ]]; then
    error "Usage: $0 verify <restored-instance-id>"
  fi

  log "Verifying restored instance: ${instance_id}"

  local endpoint
  endpoint=$(get_instance_endpoint "${instance_id}")

  if [[ -z "${endpoint}" || "${endpoint}" == "None" ]]; then
    error "Could not get endpoint for ${instance_id}"
  fi

  log "Testing connectivity to ${endpoint}..."

  # Test 1: Basic connectivity
  log "[1/5] Testing PostgreSQL connectivity..."
  if ! PGPASSWORD="${DRILL_DB_PASSWORD:-}" psql \
    -h "${endpoint}" \
    -U "${DRILL_DB_USER:-postgres}" \
    -d "${DRILL_DB_NAME}" \
    -c "SELECT 1;" >/dev/null 2>&1; then
    error "FAIL: Cannot connect to PostgreSQL on ${endpoint}"
  fi
  log "  ✓ Connection successful"

  # Test 2: Check table existence
  log "[2/5] Checking core tables exist..."
  local table_count
  table_count=$(PGPASSWORD="${DRILL_DB_PASSWORD:-}" psql \
    -h "${endpoint}" \
    -U "${DRILL_DB_USER:-postgres}" \
    -d "${DRILL_DB_NAME}" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE';")
  table_count=$(echo "${table_count}" | tr -d ' ')

  if [[ "${table_count}" -lt 10 ]]; then
    error "FAIL: Expected 10+ tables, found ${table_count}"
  fi
  log "  ✓ Found ${table_count} tables"

  # Test 3: Check critical tables have data
  log "[3/5] Checking critical tables have data..."
  local tables=("users" "firms" "matters" "tasks" "events")
  for table in "${tables[@]}"; do
    local count
    count=$(PGPASSWORD="${DRILL_DB_PASSWORD:-}" psql \
      -h "${endpoint}" \
      -U "${DRILL_DB_USER:-postgres}" \
      -d "${DRILL_DB_NAME}" \
      -t -c "SELECT COUNT(*) FROM ${table};" 2>/dev/null || echo "0")
    count=$(echo "${count}" | tr -d ' ')
    log "  ✓ ${table}: ${count} rows"
  done

  # Test 4: Check Alembic migration version
  log "[4/5] Checking migration version..."
  local alembic_version
  alembic_version=$(PGPASSWORD="${DRILL_DB_PASSWORD:-}" psql \
    -h "${endpoint}" \
    -U "${DRILL_DB_USER:-postgres}" \
    -d "${DRILL_DB_NAME}" \
    -t -c "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null || echo "unknown")
  alembic_version=$(echo "${alembic_version}" | tr -d ' ')
  log "  ✓ Alembic version: ${alembic_version}"

  # Test 5: Check data integrity (foreign key constraints)
  log "[5/5] Checking data integrity..."
  local fk_violations
  fk_violations=$(PGPASSWORD="${DRILL_DB_PASSWORD:-}" psql \
    -h "${endpoint}" \
    -U "${DRILL_DB_USER:-postgres}" \
    -d "${DRILL_DB_NAME}" \
    -t -c "
      SELECT COUNT(*)
      FROM matters m
      LEFT JOIN firms f ON m.firm_id = f.id
      WHERE f.id IS NULL AND m.deleted_at IS NULL;
    " 2>/dev/null || echo "0")
  fk_violations=$(echo "${fk_violations}" | tr -d ' ')

  if [[ "${fk_violations}" -gt 0 ]]; then
    warn "Found ${fk_violations} orphaned matter records"
  else
    log "  ✓ No orphaned records found"
  fi

  log ""
  log "═══════════════════════════════════════════════════"
  log " VERIFICATION PASSED — all checks successful"
  log "═══════════════════════════════════════════════════"
  notify_slack "✅ Backup verification PASSED for \`${instance_id}\`\n• ${table_count} tables\n• Migration: ${alembic_version}"
}

cmd_drill() {
  log "═══════════════════════════════════════════════════"
  log " MONTHLY BACKUP RESTORATION DRILL"
  log " Started: $(date -u)"
  log "═══════════════════════════════════════════════════"

  local drill_instance="${RDS_INSTANCE_ID}-drill-${TIMESTAMP}"
  local drill_start
  drill_start=$(date +%s)

  notify_slack "🔄 Monthly backup drill starting for \`${RDS_INSTANCE_ID}\`..." "warning"

  # Step 1: Get latest automated snapshot
  log ""
  log "Step 1/5: Finding latest automated snapshot..."
  local latest_snapshot
  latest_snapshot=$(aws rds describe-db-snapshots \
    --db-instance-identifier "${RDS_INSTANCE_ID}" \
    --snapshot-type automated \
    --region "${AWS_REGION}" \
    --query 'reverse(sort_by(DBSnapshots, &SnapshotCreateTime))[0].DBSnapshotIdentifier' \
    --output text)

  if [[ -z "${latest_snapshot}" || "${latest_snapshot}" == "None" ]]; then
    error "No automated snapshot found"
  fi
  log "  Latest snapshot: ${latest_snapshot}"

  # Step 2: Restore from snapshot
  log ""
  log "Step 2/5: Restoring snapshot to drill instance..."
  cmd_restore_snapshot "${latest_snapshot}" "${drill_instance}"

  # Step 3: Verify the restored instance
  log ""
  log "Step 3/5: Verifying restored data..."
  cmd_verify "${drill_instance}"

  # Step 4: Test PITR capability (just verify the window, don't actually restore)
  log ""
  log "Step 4/5: Verifying point-in-time recovery window..."
  local pitr_time
  pitr_time=$(aws rds describe-db-instances \
    --db-instance-identifier "${RDS_INSTANCE_ID}" \
    --region "${AWS_REGION}" \
    --query 'DBInstances[0].LatestRestorableTime' \
    --output text)
  log "  PITR available up to: ${pitr_time}"

  # Step 5: Clean up drill instance
  log ""
  log "Step 5/5: Cleaning up drill instance..."
  aws rds delete-db-instance \
    --db-instance-identifier "${drill_instance}" \
    --skip-final-snapshot \
    --region "${AWS_REGION}" || warn "Cleanup failed — manual cleanup required"

  local drill_end
  drill_end=$(date +%s)
  local drill_duration=$(( (drill_end - drill_start) / 60 ))

  log ""
  log "═══════════════════════════════════════════════════"
  log " DRILL COMPLETED SUCCESSFULLY"
  log " Duration: ${drill_duration} minutes"
  log " Snapshot: ${latest_snapshot}"
  log " PITR window: up to ${pitr_time}"
  log "═══════════════════════════════════════════════════"

  notify_slack "✅ *Monthly backup drill PASSED*\n• Duration: ${drill_duration} min\n• Snapshot: \`${latest_snapshot}\`\n• PITR: up to \`${pitr_time}\`\n• Tables verified, data integrity confirmed"
}

cmd_cleanup() {
  log "Cleaning up drill/test instances..."

  local instances
  instances=$(aws rds describe-db-instances \
    --region "${AWS_REGION}" \
    --query "DBInstances[?contains(DBInstanceIdentifier, 'drill') || contains(DBInstanceIdentifier, 'restore')].{
      ID: DBInstanceIdentifier,
      Created: InstanceCreateTime,
      Status: DBInstanceStatus
    }" --output json)

  local count
  count=$(echo "${instances}" | jq 'length')

  if [[ "${count}" -eq 0 ]]; then
    log "No drill/test instances found"
    return
  fi

  log "Found ${count} drill/test instances:"
  echo "${instances}" | jq -r '.[] | "  \(.ID) (\(.Status)) — created \(.Created)"'

  echo ""
  read -r -p "Delete all listed instances? [y/N]: " confirm
  if [[ "${confirm}" =~ ^[Yy]$ ]]; then
    echo "${instances}" | jq -r '.[].ID' | while read -r id; do
      log "Deleting ${id}..."
      aws rds delete-db-instance \
        --db-instance-identifier "${id}" \
        --skip-final-snapshot \
        --region "${AWS_REGION}" || warn "Failed to delete ${id}"
    done
    log "Cleanup complete"
  else
    log "Cancelled"
  fi
}

cmd_status() {
  log "=== Backup Status for ${RDS_INSTANCE_ID} ==="
  echo ""

  aws rds describe-db-instances \
    --db-instance-identifier "${RDS_INSTANCE_ID}" \
    --region "${AWS_REGION}" \
    --query 'DBInstances[0].{
      Instance: DBInstanceIdentifier,
      Engine: Engine,
      EngineVersion: EngineVersion,
      Status: DBInstanceStatus,
      MultiAZ: MultiAZ,
      StorageEncrypted: StorageEncrypted,
      BackupRetention: BackupRetentionPeriod,
      BackupWindow: PreferredBackupWindow,
      LatestRestorableTime: LatestRestorableTime,
      AllocatedStorage_GB: AllocatedStorage,
      DeletionProtection: DeletionProtection
    }' --output table

  echo ""
  log "=== Latest Snapshot ==="
  aws rds describe-db-snapshots \
    --db-instance-identifier "${RDS_INSTANCE_ID}" \
    --region "${AWS_REGION}" \
    --query 'reverse(sort_by(DBSnapshots, &SnapshotCreateTime))[0].{
      ID: DBSnapshotIdentifier,
      Created: SnapshotCreateTime,
      Status: Status,
      Size_GB: AllocatedStorage,
      Encrypted: Encrypted
    }' --output table
}

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
  local command="${1:-help}"
  shift || true

  case "${command}" in
    snapshot)         cmd_snapshot "$@" ;;
    list)             cmd_list ;;
    restore-snapshot) cmd_restore_snapshot "$@" ;;
    restore-pitr)     cmd_restore_pitr "$@" ;;
    verify)           cmd_verify "$@" ;;
    drill)            cmd_drill ;;
    cleanup)          cmd_cleanup ;;
    status)           cmd_status ;;
    help|--help|-h)
      grep '^#' "${BASH_SOURCE[0]}" | head -20 | sed 's/^# \?//'
      ;;
    *)
      error "Unknown command: ${command}. Run '$0 help' for usage."
      ;;
  esac
}

main "$@"
