#!/usr/bin/env bash
# verify_sprint24.sh — Commercial visual asset upgrade verification.

set -eu
cd "$(dirname "$0")/.."

PASS=0
FAIL=0
WARN=0

pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  [WARN] $1"; WARN=$((WARN + 1)); }
section() { echo; echo "── $1 ──"; }

PRODUCT_DIR="products/product_43"
COVERS_DIR="$PRODUCT_DIR/covers"
VISUALS_DIR="$PRODUCT_DIR/marketplace_visuals"

echo "═══════════════════════════════════════════════════════════"
echo "  HYDRA Sprint 2.4 — Commercial Visual Verification"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════════"

section "Static Code"
python3 -m py_compile app/kit_covers.py app/kit_generator.py app/kit_routes.py 2>/dev/null \
  && pass "Kit visual Python files compile" || fail "Python compile failed"
grep -q "build_marketplace_visuals" app/kit_covers.py \
  && pass "Marketplace visual builder exists" || fail "Marketplace visual builder missing"
grep -q "sequence-strip" app/templates/kit_document.html \
  && pass "Document sequence indicator exists" || fail "Document sequence indicator missing"
grep -q "COPY / PASTE ASSET" app/templates/kit_document.html \
  && pass "Prompt asset styling exists" || fail "Prompt asset styling missing"

section "Cover Assets"
for f in cover_MASTER.svg cover_00.svg cover_01.svg cover_02.svg cover_03.svg cover_04.svg cover_05.svg cover_06.svg cover_07.svg; do
  [ -f "$COVERS_DIR/$f" ] && pass "$f exists" || fail "$f missing"
done
grep -q "PREMIUM BUSINESS TOOLKIT" "$COVERS_DIR/cover_MASTER.svg" \
  && pass "Master cover has premium positioning" || fail "Master cover not upgraded"
grep -q "WHAT THIS UNLOCKS" "$COVERS_DIR/cover_02.svg" \
  && pass "Document cover has value panel" || fail "Document cover value panel missing"

section "Marketplace Visuals"
[ -d "$VISUALS_DIR" ] && pass "marketplace_visuals folder exists" || fail "marketplace_visuals folder missing"
[ -f "$VISUALS_DIR/fiverr_gig_image_1280x769.svg" ] && pass "Fiverr gig image exists" || fail "Fiverr gig image missing"
grep -q 'width="1280" height="769"' "$VISUALS_DIR/fiverr_gig_image_1280x769.svg" \
  && pass "Fiverr image is 1280x769" || fail "Fiverr image dimensions wrong"
[ -f "$VISUALS_DIR/gumroad_cover.svg" ] && pass "Gumroad cover exists" || fail "Gumroad cover missing"
[ -f "$VISUALS_DIR/value_stack.svg" ] && pass "Value stack visual exists" || fail "Value stack visual missing"
[ -f "$VISUALS_DIR/product_mockup.svg" ] && pass "Product mockup visual exists" || fail "Product mockup visual missing"
[ -f "$VISUALS_DIR/eight_documents_included.svg" ] && pass "8 documents included visual exists" || fail "8 documents visual missing"
[ -f "$VISUALS_DIR/payhip_sellfy_cover.svg" ] && pass "Payhip/Sellfy cover exists" || fail "Payhip/Sellfy cover missing"

section "Documents And Package"
html_count=$(find "$PRODUCT_DIR" -maxdepth 1 -name '*.html' | wc -l)
[ "$html_count" -ge 8 ] && pass "$html_count HTML documents present" || fail "Only $html_count HTML documents present"
pdf_count=$(find "$PRODUCT_DIR" -maxdepth 1 -name '*.pdf' ! -name 'MASTER_*' | wc -l)
[ "$pdf_count" -ge 8 ] && pass "$pdf_count individual PDFs present" || fail "Only $pdf_count individual PDFs present"
[ -f "$PRODUCT_DIR/MASTER_Complete_Kit.pdf" ] && pass "Master PDF exists" || fail "Master PDF missing"
zip_count=$(find "$PRODUCT_DIR" -maxdepth 1 -name '*.zip' | wc -l)
[ "$zip_count" -ge 1 ] && pass "$zip_count delivery ZIP(s) exist" || fail "Delivery ZIP missing"

if grep -R -q -E "CONTENT PENDING|LLM generation was not available" "$PRODUCT_DIR"/*.html 2>/dev/null; then
  fail "Fallback placeholder text found"
else
  pass "No fallback placeholder text found"
fi

section "Visual QA Report"
[ -f "$PRODUCT_DIR/quality/visual_commercial_review.md" ] \
  && pass "visual_commercial_review.md exists" || fail "visual_commercial_review.md missing"
grep -q "Good enough for first Gumroad/Fiverr listing" "$PRODUCT_DIR/quality/visual_commercial_review.md" \
  && pass "Visual review states listability" || warn "Visual review does not state listability"

if [ "${LIVE:-0}" = "1" ]; then
  section "Live Routes"
  BASE="${HYDRA_BASE_URL:-http://localhost:8000}"
  AUTH_USER="${HYDRA_BASIC_USER:-admin}"
  AUTH_PASS="${HYDRA_BASIC_PASS:-change-me}"
  code=$(curl -s -u "$AUTH_USER:$AUTH_PASS" -o /dev/null -w "%{http_code}" "$BASE/kits/43" 2>/dev/null || echo "0")
  [ "$code" = "200" ] && pass "GET /kits/43 -> 200" || fail "GET /kits/43 -> $code"
fi

echo
echo "═══════════════════════════════════════════════════════════"
echo "  Results: $PASS PASS | $FAIL FAIL | $WARN WARN"
echo "═══════════════════════════════════════════════════════════"
[ "$FAIL" -eq 0 ]
