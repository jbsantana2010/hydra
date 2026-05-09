#!/usr/bin/env bash
# backup_db.sh — dump the HYDRA Postgres database to a timestamped file.
#
# Usage:
#   ./scripts/backup_db.sh                  # default: backups/ in project root
#   BACKUP_DIR=/mnt/safe/backups ./scripts/backup_db.sh
#
# Env vars honoured (same as docker-compose.yml defaults):
#   POSTGRES_DB   default: hydra
#   POSTGRES_USER default: hydra
#   POSTGRES_HOST default: localhost
#   POSTGRES_PORT default: 5432
#   BACKUP_DIR    default: <project-root>/backups
#
# Requires: pg_dump available in PATH (usually via postgresql-client package
#           or inside the postgres container).  When running from the host,
#           call through docker compose exec:
#
#   docker compose exec db pg_dump -U hydra hydra | gzip > backups/hydra_$(date +%Y%m%d_%H%M%S).sql.gz
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

DB_NAME="${POSTGRES_DB:-hydra}"
DB_USER="${POSTGRES_USER:-hydra}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"

mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="$BACKUP_DIR/hydra_${TIMESTAMP}.sql.gz"

echo "[backup_db] Dumping $DB_NAME → $OUTFILE"

PGPASSWORD="${POSTGRES_PASSWORD:-hydra}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    --format=plain \
    --no-owner \
    --no-acl \
    "$DB_NAME" \
  | gzip -9 > "$OUTFILE"

echo "[backup_db] Done. File size: $(du -sh "$OUTFILE" | cut -f1)"
echo "[backup_db] Path: $OUTFILE"
