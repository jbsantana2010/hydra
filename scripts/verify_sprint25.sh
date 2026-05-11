#!/usr/bin/env bash
# verify_sprint25.sh — Marketplace visual refinement + palette variants.

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
VISUALS_DIR="$PRODUCT_DIR/marketplace_visuals"
VARIANTS_DIR="$VISUALS_DIR/variants"
THEMES="navy_gold charcoal_emerald white_navy_gold deep_teal_copper black_platinum_blue"
FILES="gumroad_cover.svg fiverr_gig_image_1280x769.svg value_stack.svg product_mockup.svg eight_documents_included.svg"

echo "═══════════════════════════════════════════════════════════"
echo "  HYDRA Sprint 2.5 — Marketplace Visual Variants"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════════"

section "Static Code"
python3 -m py_compile app/kit_covers.py app/kit_generator.py app/kit_routes.py 2>/dev/null \
  && pass "Kit visual code compiles" || fail "Kit visual code compile failed"
for token in "title_box_width" "module_grid_x" "card_width" "safe_bottom_y" "PALETTES" "build_palette_variants"; do
  grep -q "$token" app/kit_covers.py && pass "kit_covers.py has $token" || fail "kit_covers.py missing $token"
done

section "Main Marketplace Visuals"
for file in gumroad_cover.svg fiverr_gig_image_1280x769.svg value_stack.svg product_mockup.svg eight_documents_included.svg payhip_sellfy_cover.svg; do
  path="$VISUALS_DIR/$file"
  [ -s "$path" ] && pass "$file exists and is non-empty" || fail "$file missing or empty"
done
grep -q 'width="1280" height="769"' "$VISUALS_DIR/fiverr_gig_image_1280x769.svg" \
  && pass "Main Fiverr image is 1280x769" || fail "Main Fiverr image dimensions wrong"
grep -q 'viewBox="0 0 1280 769"' "$VISUALS_DIR/fiverr_gig_image_1280x769.svg" \
  && pass "Main Fiverr image viewBox is 1280x769" || fail "Main Fiverr viewBox wrong"
grep -q "BUYER OUTCOME" "$VISUALS_DIR/gumroad_cover.svg" \
  && pass "Gumroad cover has stronger buyer-outcome copy" || fail "Gumroad cover missing buyer-outcome copy"

section "Palette Variants"
[ -d "$VARIANTS_DIR" ] && pass "variants folder exists" || fail "variants folder missing"
count=$(find "$VARIANTS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)
[ "$count" -ge 5 ] && pass "$count variant folders exist" || fail "Only $count variant folders exist"
for theme in $THEMES; do
  [ -d "$VARIANTS_DIR/$theme" ] && pass "$theme folder exists" || fail "$theme folder missing"
  for file in $FILES; do
    path="$VARIANTS_DIR/$theme/$file"
    [ -s "$path" ] && pass "$theme/$file exists" || fail "$theme/$file missing or empty"
  done
  grep -q 'width="1280" height="769"' "$VARIANTS_DIR/$theme/fiverr_gig_image_1280x769.svg" \
    && pass "$theme Fiverr dimensions OK" || fail "$theme Fiverr dimensions wrong"
  grep -q 'viewBox="0 0 1280 769"' "$VARIANTS_DIR/$theme/fiverr_gig_image_1280x769.svg" \
    && pass "$theme Fiverr viewBox OK" || fail "$theme Fiverr viewBox wrong"
done

section "Variant Index And Notes"
[ -s "$VARIANTS_DIR/index.html" ] && pass "variants/index.html exists" || fail "variants/index.html missing"
for theme in Navy "Charcoal Emerald" "White Navy Gold" "Deep Teal Copper" "Black Platinum Blue"; do
  grep -q "$theme" "$VARIANTS_DIR/index.html" && pass "index includes $theme" || fail "index missing $theme"
done
[ -s "$VARIANTS_DIR/export_notes.md" ] && pass "export_notes.md exists" || fail "export_notes.md missing"
grep -q "Recommended theme: \\*\\*Navy Gold\\*\\*" "$VARIANTS_DIR/export_notes.md" \
  && pass "Export notes recommend Navy Gold" || warn "Export notes do not recommend Navy Gold"

section "Product 43 Regression"
html_count=$(find "$PRODUCT_DIR" -maxdepth 1 -name '*.html' | wc -l)
[ "$html_count" -ge 8 ] && pass "$html_count HTML docs present" || fail "Only $html_count HTML docs"
pdf_count=$(find "$PRODUCT_DIR" -maxdepth 1 -name '*.pdf' ! -name 'MASTER_*' | wc -l)
[ "$pdf_count" -ge 8 ] && pass "$pdf_count individual PDFs present" || fail "Only $pdf_count individual PDFs"
[ -f "$PRODUCT_DIR/MASTER_Complete_Kit.pdf" ] && pass "Master PDF exists" || fail "Master PDF missing"
if grep -R -q -E "CONTENT PENDING|LLM generation was not available" "$PRODUCT_DIR"/*.html 2>/dev/null; then
  fail "Fallback placeholder text found"
else
  pass "No fallback placeholder text found"
fi

if [ "${LIVE:-0}" = "1" ]; then
  section "Live Build Check"
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
