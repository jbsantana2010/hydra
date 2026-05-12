#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PRODUCT_ID="${PRODUCT_ID:-43}"
PRODUCT_DIR="products/product_${PRODUCT_ID}"
VISUALS_DIR="$PRODUCT_DIR/marketplace_visuals"
QUALITY_DIR="$PRODUCT_DIR/quality"
THEMES="navy_gold charcoal_emerald white_navy_gold deep_teal_copper black_platinum_blue"
failures=0

pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1"; failures=$((failures + 1)); }
check_file() { [[ -s "$1" ]] && pass "$2" || fail "$2"; }
check_grep() { grep -q "$1" "$2" && pass "$3" || fail "$3"; }

echo "HYDRA Sprint 2.8.1 — Marketplace Visual Consistency Fix"

python3 -m py_compile app/kit_covers.py app/aesthetica.py \
  && pass "visual modules compile" || fail "visual modules compile"

for token in "BUYER_OUTCOME_COPY" "_estimated_text_width" "text_overflow_issues" "left_column_width" "right_visual_x"; do
  check_grep "$token" app/kit_covers.py "kit_covers.py includes $token"
done

python3 scripts/build_product43_kit.py --covers-only >/tmp/hydra_sprint281_build.out \
  && pass "Product ${PRODUCT_ID} visuals regenerated" || {
    cat /tmp/hydra_sprint281_build.out || true
    fail "Product ${PRODUCT_ID} visuals regenerated"
  }

for file in gumroad_cover.svg fiverr_gig_image_1280x769.svg product_mockup.svg value_stack.svg eight_documents_included.svg payhip_sellfy_cover.svg; do
  check_file "$VISUALS_DIR/$file" "$file exists"
done

for theme in $THEMES; do
  for file in gumroad_cover.svg fiverr_gig_image_1280x769.svg product_mockup.svg value_stack.svg eight_documents_included.svg; do
    check_file "$VISUALS_DIR/variants/$theme/$file" "$theme/$file exists"
  done
done

PYTHONPATH=app python3 - <<PY
import json
from pathlib import Path
from aesthetica import run_aesthetica_review

product_id = $PRODUCT_ID
layout_path = Path(f"products/product_{product_id}/quality/layout_safety_report.json")
layout = json.loads(layout_path.read_text())
assert layout["status"] == "PASS", layout["status"]
assert layout["fail_count"] == 0, layout["fail_count"]

required = {
    "gumroad_cover.svg",
    "fiverr_gig_image_1280x769.svg",
    "payhip_sellfy_cover.svg",
}
main = [a for a in layout["assets"] if a["scope"] == "main" and Path(a["filename"]).name in required]
assert len(main) == len(required), main
for asset in main:
    assert asset["status"] == "PASS", asset
    assert not asset["text_overflow_issues"], asset["text_overflow_issues"]
    assert not asset["safe_zone_issues"], asset["safe_zone_issues"]
    assert not asset["collisions_found"], asset["collisions_found"]

for asset in layout["assets"]:
    assert not asset["text_overflow_issues"], (asset["filename"], asset["text_overflow_issues"])
    assert not asset["safe_zone_issues"], (asset["filename"], asset["safe_zone_issues"])
    assert not asset["collisions_found"], (asset["filename"], asset["collisions_found"])

report = run_aesthetica_review(product_id)
assert report["layout_safety"]["status"] == "PASS", report["layout_safety"]
assert report["layout_safety"]["launch_blocker"] is False, report["layout_safety"]
assert report["launch_ready"] is True, report["launch_ready"]
print("layout", layout["status"], layout["asset_count"], "aesthetica", report["overall_score"])
PY
pass "layout safety, text overflow, and AESTHETICA checks pass"

check_grep "Save hours on listings, follow-up, and reviews." "$VISUALS_DIR/gumroad_cover.svg" "Gumroad uses shortened buyer outcome"
check_grep "Save hours on listings, follow-up, and reviews." "$VISUALS_DIR/fiverr_gig_image_1280x769.svg" "Fiverr uses shortened buyer outcome"
check_grep "Save hours on listings, follow-up, and reviews." "$VISUALS_DIR/payhip_sellfy_cover.svg" "Payhip/Sellfy uses shortened buyer outcome"
check_grep "Layout PASS" "$VISUALS_DIR/variants/index.html" "variant index shows layout PASS"

LIVE=0 bash scripts/verify_sprint28.sh >/tmp/hydra_sprint28_regression.out \
  && pass "Sprint 2.8 regression passes" || {
    cat /tmp/hydra_sprint28_regression.out || true
    fail "Sprint 2.8 regression passes"
  }

LIVE=0 bash scripts/verify_sprint26.sh >/tmp/hydra_sprint26_regression.out \
  && pass "Sprint 2.6 regression passes" || {
    cat /tmp/hydra_sprint26_regression.out || true
    fail "Sprint 2.6 regression passes"
  }

if [[ "$failures" -eq 0 ]]; then
  echo "SPRINT 2.8.1 VERIFY: PASS"
else
  echo "SPRINT 2.8.1 VERIFY: FAIL ($failures)"
  exit 1
fi
