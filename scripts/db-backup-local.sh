#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Local Development Database Backup & Restore
#
# For the Docker Compose PostgreSQL instance (development only).
#
# Usage:
#   ./scripts/db-backup-local.sh dump    [filename]   — Dump to SQL file
#   ./scripts/db-backup-local.sh restore <filename>   — Restore from dump
#   ./scripts/db-backup-local.sh list                 — List local backups
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

BACKUP_DIR="./backups"
DB_CONTAINER="$(docker compose ps -q postgres 2>/dev/null || echo '')"
DB_USER="postgres"
DB_NAME="estate_executor"

mkdir -p "${BACKUP_DIR}"

case "${1:-help}" in
  dump)
    FILENAME="${2:-${BACKUP_DIR}/estate_executor_$(date +%Y%m%d_%H%M%S).sql.gz}"
    echo "Dumping database to ${FILENAME}..."
    docker compose exec -T postgres pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "${FILENAME}"
    echo "Done. Size: $(du -h "${FILENAME}" | cut -f1)"
    ;;

  restore)
    FILE="${2:-}"
    if [[ -z "${FILE}" ]]; then
      echo "Usage: $0 restore <backup-file>"
      exit 1
    fi
    echo "Restoring from ${FILE}..."
    echo "WARNING: This will DROP and recreate the database."
    read -r -p "Continue? [y/N]: " confirm
    if [[ "${confirm}" =~ ^[Yy]$ ]]; then
      docker compose exec -T postgres dropdb -U "${DB_USER}" --if-exists "${DB_NAME}"
      docker compose exec -T postgres createdb -U "${DB_USER}" "${DB_NAME}"
      gunzip -c "${FILE}" | docker compose exec -T postgres psql -U "${DB_USER}" "${DB_NAME}"
      echo "Restore complete."
    fi
    ;;

  list)
    echo "Local backups in ${BACKUP_DIR}/:"
    ls -lh "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || echo "  (none)"
    ;;

  *)
    echo "Usage: $0 {dump|restore|list} [args]"
    ;;
esac
