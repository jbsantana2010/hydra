#!/usr/bin/env bash
# restore_db.sh — restore the HYDRA Postgres database from a backup file.
#
# Usage:
#   ./scripts/restore_db.sh backups/hydra_20260509_120000.sql.gz
#
# WARNING: This DROPS and re-creates the target database. Use only in dev/staging
#          or when you fully intend to wipe current data. Requires confirmation.
#
# Env vars honoured (same as backup_db.sh):
#   POSTGRES_DB       default: hydra
#   POSTGRES_USER     default: hydra
#   POSTGRES_HOST     default: localhost
#   POSTGRES_PORT     default: 5432
#   POSTGRES_PASSWORD default: hydra
#
set -euo pipefail

BACKUP_FILE="${1:-}"
if [[ -z "$BACKUP_FILE" ]]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "[restore_db] ERROR: file not found: $BACKUP_FILE"
    exit 1
fi

DB_NAME="${POSTGRES_DB:-hydra}"
DB_USER="${POSTGRES_USER:-hydra}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

echo ""
echo "⚠️  WARNING: This will DROP and restore database '$DB_NAME' on $DB_HOST:$DB_PORT."
echo "   Backup file: $BACKUP_FILE"
echo ""
read -r -p "Type YES to continue: " CONFIRM
if [[ "$CONFIRM" != "YES" ]]; then
    echo "[restore_db] Aborted."
    exit 0
fi

echo "[restore_db] Dropping and re-creating $DB_NAME ..."
PGPASSWORD="${POSTGRES_PASSWORD:-hydra}" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
    -c "DROP DATABASE IF EXISTS $DB_NAME;" postgres

PGPASSWORD="${POSTGRES_PASSWORD:-hydra}" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
    -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" postgres

echo "[restore_db] Restoring from $BACKUP_FILE ..."
gunzip -c "$BACKUP_FILE" | PGPASSWORD="${POSTGRES_PASSWORD:-hydra}" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
    -d "$DB_NAME" \
    --quiet

echo "[restore_db] Done. Database '$DB_NAME' restored from $BACKUP_FILE"
