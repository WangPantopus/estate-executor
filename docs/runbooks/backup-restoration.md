# Database Backup & Restoration Runbook

> **Last updated:** 2026-03-24
> **Owner:** Platform Team
> **Review cadence:** Quarterly

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Backup Configuration](#2-backup-configuration)
3. [Routine Operations](#3-routine-operations)
4. [Emergency Restoration Procedures](#4-emergency-restoration-procedures)
5. [Monthly Backup Drill](#5-monthly-backup-drill)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        us-east-1 (Primary)                      │
│                                                                 │
│   ┌──────────────────┐    ┌──────────────────┐                  │
│   │  RDS PostgreSQL  │───▶│ Automated Backup │                  │
│   │  (Multi-AZ)      │    │ Daily @ 03:00 UTC│                  │
│   │  16.x            │    │ 30-day retention  │                  │
│   └──────────────────┘    └────────┬─────────┘                  │
│                                    │                             │
│   ┌──────────────────┐             │ Cross-region                │
│   │  Manual Snapshots│             │ replication                 │
│   │  (on-demand)     │             │                             │
│   └──────────────────┘             ▼                             │
│                           ┌──────────────────┐                   │
│                           │ us-west-2 (DR)   │                   │
│                           │ Backup replica   │                   │
│                           │ 30-day retention │                   │
│                           └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

**Key parameters:**

| Setting                  | Value                  |
|--------------------------|------------------------|
| Engine                   | PostgreSQL 16          |
| Multi-AZ                 | Yes (synchronous)      |
| Backup retention         | 30 days                |
| Backup window            | 03:00–04:00 UTC        |
| PITR granularity         | ~5 minutes             |
| Cross-region replica     | us-west-2              |
| Encryption               | AES-256 (AWS KMS)      |
| Deletion protection      | Enabled                |

---

## 2. Backup Configuration

### 2.1 Automated Daily Backups

AWS RDS creates automated snapshots daily during the backup window. These are:
- **Incremental** (only changed blocks are stored)
- **Encrypted** with the estate-executor KMS key
- **Retained** for 30 days
- **Replicated** to us-west-2 for disaster recovery

No action needed — automated by AWS.

### 2.2 Point-in-Time Recovery (PITR)

RDS continuously backs up transaction logs to S3, enabling recovery to any
second within the retention period.

- **Recovery Point Objective (RPO):** ~5 minutes
- **Recovery Time Objective (RTO):** 15–45 minutes (depends on DB size)

### 2.3 Manual Snapshots

Create manual snapshots before risky operations:

```bash
# Before a major migration
./scripts/db-backup.sh snapshot "Pre-migration v2.1.0"

# List all snapshots
./scripts/db-backup.sh list
```

### 2.4 Cross-Region Replication

Automated backups are replicated to us-west-2 with the same 30-day retention.
This protects against:
- Regional AWS outage
- Primary region disaster
- Accidental deletion of primary instance

---

## 3. Routine Operations

### 3.1 Check Backup Status

```bash
./scripts/db-backup.sh status
```

Verify:
- `BackupRetention` = 30
- `LatestRestorableTime` is within the last 10 minutes
- `StorageEncrypted` = True
- `MultiAZ` = True

### 3.2 Create Manual Snapshot

```bash
# Before a risky deployment
./scripts/db-backup.sh snapshot "Pre-release v2.3.0"

# Before a bulk data migration
./scripts/db-backup.sh snapshot "Pre-data-migration 2026-03"
```

### 3.3 List Available Backups

```bash
./scripts/db-backup.sh list
```

Shows:
- PITR recovery window (latest restorable time)
- Last 10 snapshots (automated + manual)
- Cross-region replication status

---

## 4. Emergency Restoration Procedures

### 4.1 Scenario: Data Corruption / Bad Migration

**Impact:** Application data is corrupted. Users see incorrect data.

**Steps:**

1. **Identify the corruption time** (check application logs, user reports)

2. **Stop writes** to prevent further corruption:
   ```bash
   # Scale API to 0
   aws ecs update-service --cluster estate-executor-production \
     --service estate-executor-api-production --desired-count 0
   ```

3. **Restore to point before corruption:**
   ```bash
   # Restore to 5 minutes before the bad deployment
   ./scripts/db-backup.sh restore-pitr "2026-03-24T14:25:00Z" estate-executor-recovery
   ```

4. **Verify the restored instance:**
   ```bash
   ./scripts/db-backup.sh verify estate-executor-recovery
   ```

5. **Update application to point to recovered instance:**
   ```bash
   # Update RDS endpoint in AWS Secrets Manager
   aws secretsmanager update-secret --secret-id prod/database-url \
     --secret-string "postgresql+asyncpg://user:pass@<new-endpoint>:5432/estate_executor"

   # Restart API service
   aws ecs update-service --cluster estate-executor-production \
     --service estate-executor-api-production --desired-count 2 --force-new-deployment
   ```

6. **Verify application health:**
   ```bash
   curl -sf https://api.estate-executor.com/api/v1/health/ready | jq .
   ```

7. **Clean up original (corrupted) instance** after confirming recovery.

### 4.2 Scenario: Complete Instance Failure

**Impact:** RDS instance is unavailable. 500 errors for all API requests.

**Steps:**

1. **Check if Multi-AZ failover handles it automatically:**
   ```bash
   aws rds describe-events --source-identifier estate-executor-production \
     --source-type db-instance --duration 60
   ```

2. **If automatic failover didn't resolve:**
   ```bash
   # Restore from latest snapshot
   ./scripts/db-backup.sh restore-snapshot \
     "$(aws rds describe-db-snapshots \
        --db-instance-identifier estate-executor-production \
        --query 'reverse(sort_by(DBSnapshots, &SnapshotCreateTime))[0].DBSnapshotIdentifier' \
        --output text)" \
     estate-executor-recovery
   ```

3. **Follow steps 4-7 from Scenario 4.1**

### 4.3 Scenario: Regional Outage (us-east-1 down)

**Impact:** Primary region is unavailable.

**Steps:**

1. **Restore from cross-region backup in us-west-2:**
   ```bash
   AWS_REGION=us-west-2 ./scripts/db-backup.sh restore-snapshot \
     "<cross-region-snapshot-id>" estate-executor-dr
   ```

2. **Update DNS to point to us-west-2 services**

3. **Deploy application to us-west-2 ECS cluster**

4. **Update all service configurations for DR region**

> **Note:** This scenario requires a pre-configured DR ECS cluster and
> networking in us-west-2. This should be tested annually.

### 4.4 Scenario: Accidental Data Deletion

**Impact:** User or admin accidentally deleted important records.

**Steps:**

1. **Identify what was deleted and when** (check `events` audit table first):
   ```sql
   SELECT * FROM events
   WHERE action = 'deleted'
   AND created_at > '2026-03-24T10:00:00Z'
   ORDER BY created_at DESC;
   ```

2. **If soft-deleted** (most records use soft delete):
   ```sql
   -- Restore soft-deleted matters
   UPDATE matters SET deleted_at = NULL WHERE id = '<matter-id>';
   ```

3. **If hard-deleted**, use PITR:
   ```bash
   ./scripts/db-backup.sh restore-pitr "2026-03-24T09:55:00Z" estate-executor-recovery
   ```

4. **Extract needed records** from the restored instance and insert into production.

---

## 5. Monthly Backup Drill

### 5.1 Purpose

Verify that backups are restorable and data integrity is maintained. Per SOC 2
and legal compliance requirements, this drill runs monthly.

### 5.2 Automated Drill

A GitHub Actions workflow runs the drill on the 1st of each month:

```bash
# Or run manually
./scripts/db-backup.sh drill
```

### 5.3 Drill Procedure

The drill automatically:

1. Finds the latest automated snapshot
2. Restores it to a temporary `*-drill-*` instance
3. Runs verification checks:
   - PostgreSQL connectivity
   - Core tables exist (users, firms, matters, tasks, events)
   - Row counts for critical tables
   - Alembic migration version matches
   - Foreign key integrity (no orphaned records)
4. Verifies PITR window is current
5. Cleans up the drill instance
6. Reports results to Slack

### 5.4 Drill Success Criteria

| Check                       | Criteria                         |
|-----------------------------|----------------------------------|
| Snapshot restore            | Completes in < 45 minutes        |
| Database connectivity       | `SELECT 1` succeeds              |
| Table count                 | ≥ 30 tables present              |
| Critical tables             | All 5 have > 0 rows              |
| Migration version           | Matches production HEAD           |
| Data integrity              | No orphaned FK references         |
| PITR window                 | Within last 10 minutes            |

### 5.5 Drill Failure Response

If the drill fails:

1. **Check Slack** for the failure notification
2. **Review the GitHub Actions run** for detailed logs
3. **Common failures:**
   - Snapshot too old → check backup window configuration
   - Permission denied → verify IAM roles
   - Instance class unavailable → try a different class
4. **Fix the issue** and re-run the drill manually
5. **File an incident report** if backup integrity is compromised

---

## 6. Troubleshooting

### "No automated snapshot found"

```bash
# Check backup configuration
aws rds describe-db-instances --db-instance-identifier estate-executor-production \
  --query 'DBInstances[0].{BackupRetention: BackupRetentionPeriod, Window: PreferredBackupWindow}'
```

Ensure `BackupRetentionPeriod` > 0.

### "Snapshot restore taking too long"

Large databases (> 100 GB) can take 30+ minutes. Monitor progress:

```bash
aws rds describe-db-instances --db-instance-identifier <restore-id> \
  --query 'DBInstances[0].DBInstanceStatus'
```

### "PITR fails with 'invalid restore time'"

The restore time must be within the PITR window:

```bash
aws rds describe-db-instances --db-instance-identifier estate-executor-production \
  --query 'DBInstances[0].LatestRestorableTime'
```

### "Cross-region replication lag"

Check CloudWatch alarm `estate-executor-production-replication-lag`. If lag
exceeds 1 hour:

1. Check for long-running transactions in the primary
2. Verify network connectivity between regions
3. Contact AWS support if persistent

### "Drill instance won't delete"

If deletion protection is accidentally enabled:

```bash
aws rds modify-db-instance --db-instance-identifier <drill-id> \
  --no-deletion-protection --apply-immediately
# Wait a moment, then:
aws rds delete-db-instance --db-instance-identifier <drill-id> --skip-final-snapshot
```

---

## Appendix: Required IAM Permissions

The backup script and CI/CD workflows need these IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:CreateDBSnapshot",
        "rds:DeleteDBInstance",
        "rds:DescribeDBInstances",
        "rds:DescribeDBSnapshots",
        "rds:DescribeDBInstanceAutomatedBackups",
        "rds:DescribeEvents",
        "rds:RestoreDBInstanceFromDBSnapshot",
        "rds:RestoreDBInstanceToPointInTime",
        "rds:ModifyDBInstance",
        "rds:AddTagsToResource",
        "kms:CreateGrant",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Revision History

| Date       | Author        | Change                              |
|------------|---------------|-------------------------------------|
| 2026-03-24 | Platform Team | Initial runbook                     |
