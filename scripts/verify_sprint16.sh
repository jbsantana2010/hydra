#!/usr/bin/env bash
# verify_sprint16.sh — acceptance tests for Sprint 1.6 (Alembic + Backup + Listings)
#
# Usage:
#   cd /home/jb/dev/hydra
#   bash scripts/verify_sprint16.sh           # all checks (no DB required for static)
#   LIVE_DB=1 bash scripts/verify_sprint16.sh # include live DB migration checks
#
set -euo pipefail

# Always run from project root regardless of where the script is invoked from
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

PASS=0
FAIL=0
SKIP=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}PASS${NC}  $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}FAIL${NC}  $1"; FAIL=$((FAIL+1)); }
skip() { echo -e "${YELLOW}SKIP${NC}  $1 (reason: $2)"; SKIP=$((SKIP+1)); }

echo ""
echo "=============================="
echo " HYDRA Sprint 1.6 Verification"
echo "=============================="
echo ""

# ── 1. Alembic config files exist ──────────────────────────────────────────
echo "── 1. Alembic file structure ──────────────────────────────────"

REQUIRED_FILES=(
    "app/alembic.ini"
    "app/alembic/env.py"
    "app/alembic/script.py.mako"
    "app/alembic/versions/0001_baseline.py"
    "app/alembic/versions/0002_sprint16_listings.py"
)
for f in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$f" ]]; then
        pass "File exists: $f"
    else
        fail "Missing: $f"
    fi
done

# ── 2. requirements.txt has alembic ─────────────────────────────────────────
echo ""
echo "── 2. Dependencies ────────────────────────────────────────────"

if grep -q "alembic" app/requirements.txt; then
    pass "alembic in requirements.txt"
else
    fail "alembic NOT in requirements.txt"
fi

# ── 3. db.py — Listing model present ────────────────────────────────────────
echo ""
echo "── 3. db.py — Listing model ───────────────────────────────────"

if grep -q "class Listing(Base)" app/db.py; then
    pass "Listing model defined"
else
    fail "Listing model NOT found in db.py"
fi

for col in "product_id" "platform" "status" "external_id" "draft_url" "live_url" "price_cents"; do
    if grep -q "$col" app/db.py; then
        pass "Listing.${col} column present"
    else
        fail "Listing.${col} column MISSING"
    fi
done

# ── 4. db.py — init_db() uses Alembic ───────────────────────────────────────
echo ""
echo "── 4. db.py — init_db() Alembic logic ────────────────────────"

if grep -q "alembic.config" app/db.py; then
    pass "init_db() imports Alembic config"
else
    fail "init_db() does NOT import Alembic config"
fi

if grep -q "command.upgrade" app/db.py; then
    pass "init_db() calls command.upgrade"
else
    fail "init_db() missing command.upgrade"
fi

if grep -q "command.stamp" app/db.py; then
    pass "init_db() has pre-Alembic stamp fallback"
else
    fail "init_db() missing pre-Alembic stamp logic"
fi

if grep -q "_APP_DIR" app/db.py; then
    pass "_APP_DIR constant defined in db.py"
else
    fail "_APP_DIR constant MISSING from db.py"
fi

# ── 5. main.py — Listing imported ───────────────────────────────────────────
echo ""
echo "── 5. main.py — Listing integration ──────────────────────────"

if grep -q "from db import" app/main.py && grep -A 20 "from db import" app/main.py | grep -q "Listing,"; then
    pass "Listing imported in main.py"
else
    fail "Listing NOT imported in main.py"
fi

if grep -q "listings = session.scalars" app/main.py; then
    pass "edit_product queries listings"
else
    fail "edit_product does NOT query listings"
fi

if grep -q '"listings": listings' app/main.py; then
    pass "listings passed to template context"
else
    fail "listings NOT in template context"
fi

# ── 6. template — listings section present ──────────────────────────────────
echo ""
echo "── 6. product_edit.html — listings section ────────────────────"

if grep -q "Listings Tracker" app/templates/product_edit.html; then
    pass "Listings section heading found"
else
    fail "Listings section MISSING from product_edit.html"
fi

for platform in "gumroad" "etsy" "sellfy" "payhip"; do
    if grep -qi "$platform" app/templates/product_edit.html; then
        pass "Platform $platform referenced in template"
    else
        fail "Platform $platform MISSING from template"
    fi
done

# ── 7. Backup scripts exist and are executable ──────────────────────────────
echo ""
echo "── 7. Backup / restore scripts ───────────────────────────────"

for script in "scripts/backup_db.sh" "scripts/restore_db.sh"; do
    if [[ -f "$script" ]]; then
        pass "Script exists: $script"
        chmod +x "$script"
        pass "chmod +x $script"
    else
        fail "Missing: $script"
    fi
done

if grep -q "pg_dump" scripts/backup_db.sh; then
    pass "backup_db.sh calls pg_dump"
else
    fail "backup_db.sh missing pg_dump"
fi

if grep -q "gunzip" scripts/restore_db.sh; then
    pass "restore_db.sh calls gunzip (compressed restore)"
else
    fail "restore_db.sh missing gunzip"
fi

if grep -q "DROP DATABASE" scripts/restore_db.sh; then
    pass "restore_db.sh has DROP DATABASE guard"
else
    fail "restore_db.sh missing DROP DATABASE"
fi

if grep -q 'Type YES to continue' scripts/restore_db.sh; then
    pass "restore_db.sh requires confirmation before destructive restore"
else
    fail "restore_db.sh missing confirmation prompt"
fi

# ── 8. Python syntax check ───────────────────────────────────────────────────
echo ""
echo "── 8. Python syntax ───────────────────────────────────────────"

for pyfile in app/db.py app/main.py app/alembic/env.py \
              app/alembic/versions/0001_baseline.py \
              app/alembic/versions/0002_sprint16_listings.py; do
    if python3 -m py_compile "$pyfile" 2>/dev/null; then
        pass "SYNTAX OK: $pyfile"
    else
        fail "SYNTAX ERROR: $pyfile"
    fi
done

# ── 9. Migration revision chain ─────────────────────────────────────────────
echo ""
echo "── 9. Migration revision chain ────────────────────────────────"

if grep -q 'revision.*=.*"0001"' app/alembic/versions/0001_baseline.py; then
    pass "0001_baseline.py has revision='0001'"
else
    fail "0001_baseline.py revision string not found"
fi

if grep -q 'down_revision.*None' app/alembic/versions/0001_baseline.py; then
    pass "0001_baseline.py is root (down_revision=None)"
else
    fail "0001_baseline.py should have down_revision=None"
fi

if grep -q 'revision.*=.*"0002"' app/alembic/versions/0002_sprint16_listings.py; then
    pass "0002_sprint16_listings.py has revision='0002'"
else
    fail "0002_sprint16_listings.py revision string not found"
fi

if grep -q 'down_revision.*"0001"' app/alembic/versions/0002_sprint16_listings.py; then
    pass "0002_sprint16_listings.py links to 0001"
else
    fail "0002_sprint16_listings.py missing down_revision='0001'"
fi

# ── 10. Live DB check (optional) ────────────────────────────────────────────
echo ""
echo "── 10. Live DB integration (optional) ─────────────────────────"

if [[ "${LIVE_DB:-0}" != "1" ]]; then
    skip "alembic_version table check" "LIVE_DB=1 not set"
    skip "listings table in DB"        "LIVE_DB=1 not set"
    skip "alembic current shows 0002"  "LIVE_DB=1 not set"
else
    # Run from inside the container
    echo "  [live] Running: docker compose exec db psql -U hydra -c '\dt'"
    if docker compose exec db psql -U hydra -c "\dt" 2>/dev/null | grep -q "alembic_version"; then
        pass "alembic_version table exists in DB"
    else
        fail "alembic_version table NOT found (did init_db() run?)"
    fi

    if docker compose exec db psql -U hydra -c "\dt" 2>/dev/null | grep -q "listings"; then
        pass "listings table exists in DB"
    else
        fail "listings table NOT found (did migration 0002 run?)"
    fi

    echo "  [live] Running: docker compose exec hydra-console alembic -c app/alembic.ini current"
    if docker compose exec hydra-console alembic -c app/alembic.ini current 2>/dev/null | grep -q "0002"; then
        pass "Alembic current = 0002 (sprint16 listings)"
    else
        fail "Alembic current is NOT 0002"
    fi
fi

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "=============================="
printf " PASS: %s  FAIL: %s  SKIP: %s\n" "$PASS" "$FAIL" "$SKIP"
echo "=============================="
echo ""

if [[ "$FAIL" -gt 0 ]]; then
    echo "Sprint 1.6 verification FAILED — fix the issues above before merging."
    exit 1
else
    echo "Sprint 1.6 verification PASSED ✓"
    exit 0
fi
