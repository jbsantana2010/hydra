#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LIVE="${LIVE:-0}"
PRODUCT_ID="${PRODUCT_ID:-43}"
PRODUCT_DIR="products/product_${PRODUCT_ID}"
VISUALS_DIR="$PRODUCT_DIR/marketplace_visuals"
VARIANTS_DIR="$VISUALS_DIR/variants"
QUALITY_DIR="$PRODUCT_DIR/quality"
THEMES="navy_gold charcoal_emerald white_navy_gold deep_teal_copper black_platinum_blue"
failures=0

pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1"; failures=$((failures + 1)); }
check_file() { [[ -s "$1" ]] && pass "$2" || fail "$2"; }
check_grep() { grep -q "$1" "$2" && pass "$3" || fail "$3"; }

echo "HYDRA Sprint 2.8 — Layout Safety Verification"

python3 -m py_compile app/kit_covers.py app/aesthetica.py app/main.py \
  && pass "Python modules compile" || fail "Python modules compile"

for token in "class Rect" "validate_marketplace_layout" "layout_safety_for_asset" "build_layout_safety_report" "minimum_major_zone_gap_px"; do
  check_grep "$token" app/kit_covers.py "kit_covers.py has $token"
done

python3 scripts/build_product43_kit.py --covers-only >/tmp/hydra_sprint28_build.out \
  && pass "Product ${PRODUCT_ID} marketplace visuals regenerated" || {
    cat /tmp/hydra_sprint28_build.out || true
    fail "Product ${PRODUCT_ID} marketplace visuals regenerated"
  }

check_file "$QUALITY_DIR/layout_safety_report.json" "layout safety JSON exists"
check_file "$QUALITY_DIR/layout_safety_report.md" "layout safety markdown exists"
check_file "$QUALITY_DIR/aesthetica_review.json" "AESTHETICA JSON exists"

PYTHONPATH=app python3 - <<PY
import json
from pathlib import Path
from aesthetica import run_aesthetica_review

product_id = $PRODUCT_ID
layout = json.loads(Path(f"products/product_{product_id}/quality/layout_safety_report.json").read_text())
assert layout["status"] == "PASS", layout["status"]
assert layout["fail_count"] == 0, layout["fail_count"]
navy = [a for a in layout["assets"] if a.get("theme") == "navy_gold"]
assert navy, "no navy_gold assets in layout report"
assert all(a["status"] == "PASS" for a in navy), "navy_gold layout failure"
assert not any(a["collisions_found"] for a in navy), "navy_gold collision found"
report = run_aesthetica_review(product_id)
assert "layout_safety" in report, "AESTHETICA missing layout_safety"
assert report["layout_safety"]["status"] == "PASS", report["layout_safety"]
assert report["layout_safety"]["launch_blocker"] is False
assert all("layout_safety" in v for v in report["variant_reviews"]), "variant missing layout_safety"
print("layout", layout["status"], layout["asset_count"], "aesthetica", report["overall_score"])
PY
pass "layout report and AESTHETICA safety fields validate"

check_file "$VISUALS_DIR/gumroad_cover.svg" "main Gumroad cover exists"
check_file "$VISUALS_DIR/fiverr_gig_image_1280x769.svg" "main Fiverr image exists"
check_grep 'width="1280" height="769"' "$VISUALS_DIR/fiverr_gig_image_1280x769.svg" "main Fiverr dimensions are 1280x769"
check_grep "HYDRA_LAYOUT_SAFETY: PASS" "$VISUALS_DIR/gumroad_cover.svg" "main Gumroad SVG has PASS safety marker"

for theme in $THEMES; do
  [[ -d "$VARIANTS_DIR/$theme" ]] && pass "$theme variant folder exists" || fail "$theme variant folder exists"
  check_file "$VARIANTS_DIR/$theme/gumroad_cover.svg" "$theme Gumroad cover exists"
  check_file "$VARIANTS_DIR/$theme/fiverr_gig_image_1280x769.svg" "$theme Fiverr image exists"
  check_file "$VARIANTS_DIR/$theme/value_stack.svg" "$theme value stack exists"
  check_file "$VARIANTS_DIR/$theme/product_mockup.svg" "$theme product mockup exists"
  check_file "$VARIANTS_DIR/$theme/eight_documents_included.svg" "$theme included visual exists"
  check_grep "HYDRA_LAYOUT_SAFETY: PASS" "$VARIANTS_DIR/$theme/fiverr_gig_image_1280x769.svg" "$theme Fiverr SVG has PASS safety marker"
done

check_file "$VARIANTS_DIR/index.html" "variant index exists"
check_grep "Layout PASS" "$VARIANTS_DIR/index.html" "variant index shows layout safety status"

LIVE=0 bash scripts/verify_sprint26.sh >/tmp/hydra_sprint26_regression.out \
  && pass "Sprint 2.6 regression passes" || {
    cat /tmp/hydra_sprint26_regression.out || true
    fail "Sprint 2.6 regression passes"
  }

LIVE=0 bash scripts/verify_sprint25.sh >/tmp/hydra_sprint25_regression.out \
  && pass "Sprint 2.5 regression passes" || {
    cat /tmp/hydra_sprint25_regression.out || true
    fail "Sprint 2.5 regression passes"
  }

if [[ "$LIVE" == "1" ]]; then
  code="$(curl -sS -u "${HYDRA_BASIC_USER:-admin}:${HYDRA_BASIC_PASS:-change-me}" \
    -X POST -o /tmp/hydra_sprint28_route.out -w "%{http_code}" \
    "http://localhost:8000/products/${PRODUCT_ID}/aesthetica-review" || true)"
  if [[ "$code" == "303" || "$code" == "200" ]]; then
    pass "live AESTHETICA route still responds"
  else
    cat /tmp/hydra_sprint28_route.out || true
    fail "live AESTHETICA route still responds (HTTP $code)"
  fi
else
  pass "LIVE checks skipped"
fi

if [[ "$failures" -eq 0 ]]; then
  echo "SPRINT 2.8 VERIFY: PASS"
else
  echo "SPRINT 2.8 VERIFY: FAIL ($failures)"
  exit 1
fi
