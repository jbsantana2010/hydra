#!/usr/bin/env bash
# verify_sprint27.sh — Sprint 2.7 acceptance tests
# Tests: SVG→PNG export, ZIP integrity, launch package, DB tables, webhooks
set -euo pipefail

export PATH=/snap/docker/3505/bin:/usr/bin:/bin:$PATH

PASS=0
FAIL=0
PRODUCT_DIR="/home/jb/dev/hydra/products/product_43"

pass() { echo "  PASS: $1"; PASS=$((PASS+1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

echo "========================================"
echo " HYDRA Sprint 2.7 Verification"
echo " $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "========================================"

# -----------------------------------------------------------------------
echo ""
echo "[1] Cover PNGs exported"
PNG_COUNT=$(ls "$PRODUCT_DIR/covers/"*.png 2>/dev/null | wc -l)
if [ "$PNG_COUNT" -ge 1 ]; then
    pass "$PNG_COUNT PNG(s) in covers/"
else
    fail "No PNGs found in covers/"
fi

# -----------------------------------------------------------------------
echo ""
echo "[2] Delivery ZIP exists and is non-trivial"
ZIP_FILE=$(ls "$PRODUCT_DIR/"*.zip 2>/dev/null | grep -v "Kit_Kit" | head -1 || true)
if [ -z "$ZIP_FILE" ]; then
    fail "No ZIP file found"
else
    ZIP_SIZE_KB=$(du -k "$ZIP_FILE" | cut -f1)
    if [ "$ZIP_SIZE_KB" -gt 100 ]; then
        pass "ZIP: $(basename $ZIP_FILE) — ${ZIP_SIZE_KB}KB"
    else
        fail "ZIP too small: ${ZIP_SIZE_KB}KB (expected >100KB)"
    fi
fi

# -----------------------------------------------------------------------
echo ""
echo "[3] Launch package present"
CHECKLIST="$PRODUCT_DIR/launch/LAUNCH_CHECKLIST.md"
GUMROAD_COPY="$PRODUCT_DIR/launch/gumroad/listing_copy.txt"
FIVERR_COPY="$PRODUCT_DIR/launch/fiverr/gig_copy.txt"

[ -f "$CHECKLIST" ]     && pass "LAUNCH_CHECKLIST.md" || fail "LAUNCH_CHECKLIST.md missing"
[ -f "$GUMROAD_COPY" ]  && pass "gumroad/listing_copy.txt" || fail "gumroad/listing_copy.txt missing"
[ -f "$FIVERR_COPY" ]   && pass "fiverr/gig_copy.txt" || fail "fiverr/gig_copy.txt missing"

# -----------------------------------------------------------------------
echo ""
echo "[4] App files present"
APP_DIR="/home/jb/dev/hydra/app"
[ -f "$APP_DIR/atlas.py" ]    && pass "app/atlas.py" || fail "app/atlas.py missing"
[ -f "$APP_DIR/webhooks.py" ] && pass "app/webhooks.py" || fail "app/webhooks.py missing"

MIGRATION="$APP_DIR/alembic/versions/0004_sprint27_launch.py"
[ -f "$MIGRATION" ] && pass "alembic/versions/0004_sprint27_launch.py" || fail "0004 migration missing"

# -----------------------------------------------------------------------
echo ""
echo "[5] Container running"
if docker ps --format '{{.Names}}' | grep -q "hydra-hydra-console-1"; then
    pass "hydra-hydra-console-1 is running"
else
    fail "hydra-hydra-console-1 is NOT running"
    echo "  SKIP remaining container tests"
    echo ""; echo "PASS=$PASS FAIL=$FAIL"; exit 1
fi

# -----------------------------------------------------------------------
echo ""
echo "[6] DB tables exist"
docker exec hydra-hydra-console-1 bash -c "
cd /app
python3 -c \"
from sqlalchemy import inspect
from db import engine
tables = inspect(engine).get_table_names()
assert 'product_lifecycle' in tables, 'product_lifecycle missing'
assert 'sales' in tables, 'sales missing'
print('  tables OK')
\"" && pass "product_lifecycle + sales tables" || fail "DB tables missing"

# -----------------------------------------------------------------------
echo ""
echo "[7] Product 43 seeded in product_lifecycle"
docker exec hydra-hydra-console-1 bash -c "
cd /app
python3 -c \"
from db import SessionLocal, ProductLifecycle
db = SessionLocal()
lc = db.query(ProductLifecycle).filter_by(product_id=43).first()
assert lc is not None, 'Product 43 not in product_lifecycle'
assert lc.state in ('approved','listed','live'), f'Unexpected state: {lc.state}'
print(f'  product_id=43 state={lc.state}')
db.close()
\"" && pass "Product 43 seeded, state=approved" || fail "Product 43 not seeded"

# -----------------------------------------------------------------------
echo ""
echo "[8] Webhook endpoints return 200 (no auth)"
GR=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:8000/webhooks/gumroad \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "sale_id=verify_test&price=0&product_id=VERIFY")
[ "$GR" = "200" ] && pass "POST /webhooks/gumroad -> 200" || fail "POST /webhooks/gumroad -> $GR (expected 200)"

FV=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:8000/webhooks/fiverr \
    -H "Content-Type: application/json" -d '{}')
[ "$FV" = "200" ] && pass "POST /webhooks/fiverr -> 200" || fail "POST /webhooks/fiverr -> $FV (expected 200)"

# Clean up the $0 verify_test sale
docker exec hydra-hydra-console-1 bash -c "
cd /app
python3 -c \"
from db import SessionLocal, Sale
db = SessionLocal()
rows = db.query(Sale).filter_by(amount_usd=0).all()
for r in rows: db.delete(r)
db.commit()
db.close()
\"" 2>/dev/null

# -----------------------------------------------------------------------
echo ""
echo "[9] ATLAS functions importable"
docker exec hydra-hydra-console-1 bash -c "
cd /app
python3 -c \"
import atlas
fns = ['get_product_lifecycle','set_product_state','record_listing_url','get_revenue_summary','get_launch_summary']
for fn in fns:
    assert hasattr(atlas, fn), f'{fn} missing from atlas'
print('  all ATLAS functions present')
\"" && pass "ATLAS v0.1 API complete" || fail "ATLAS missing functions"

# -----------------------------------------------------------------------
echo ""
echo "[10] main.py includes webhook router"
docker exec hydra-hydra-console-1 grep -q "webhook_router\|webhooks" /app/main.py \
    && pass "webhooks router included in main.py" \
    || fail "webhooks router NOT found in main.py"

# -----------------------------------------------------------------------
echo ""
echo "========================================"
echo " Results: $PASS passed, $FAIL failed"
echo "========================================"

if [ "$FAIL" -eq 0 ]; then
    echo " Sprint 2.7 COMPLETE — ready to list"
    exit 0
else
    echo " Sprint 2.7 INCOMPLETE — fix failures above"
    exit 1
fi
