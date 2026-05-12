#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PRODUCT_ID="${PRODUCT_ID:-43}"
PRODUCT_DIR="products/product_${PRODUCT_ID}"
REFINED_DIR="$PRODUCT_DIR/marketplace_visuals/refined"
failures=0

pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1"; failures=$((failures + 1)); }
check_file() { [[ -s "$1" ]] && pass "$2" || fail "$2"; }
check_grep() { grep -q "$1" "$2" && pass "$3" || fail "$3"; }

echo "HYDRA Sprint 2.8.2 — Composition Simplification Verification"

python3 -m py_compile app/kit_covers.py app/aesthetica.py \
  && pass "visual modules compile" || fail "visual modules compile"

for token in "REFINED_COMPOSITIONS" "generate_refined_gumroad_cover_svg" "build_refined_marketplace_variants" "composition_overcrowded" "_composition_review"; do
  file="app/kit_covers.py"
  [[ "$token" == "composition_overcrowded" || "$token" == "_composition_review" ]] && file="app/aesthetica.py"
  check_grep "$token" "$file" "$file includes $token"
done

if [[ -s "$REFINED_DIR/minimal_enterprise/gumroad_cover.svg" ]]; then
  pass "Product ${PRODUCT_ID} refined visuals already exist"
else
  python3 scripts/build_product43_kit.py --covers-only >/tmp/hydra_sprint282_build.out \
    && pass "Product ${PRODUCT_ID} visuals regenerated" || {
      cat /tmp/hydra_sprint282_build.out || true
      fail "Product ${PRODUCT_ID} visuals regenerated"
    }
fi

for style in minimal_enterprise premium_course modern_consulting; do
  check_file "$REFINED_DIR/$style/gumroad_cover.svg" "$style refined Gumroad cover exists"
  check_grep "HYDRA_COMPOSITION_REFINED: $style" "$REFINED_DIR/$style/gumroad_cover.svg" "$style has refined marker"
  check_grep "PREMIUM BUSINESS KIT" "$REFINED_DIR/$style/gumroad_cover.svg" "$style has restrained eyebrow"
  if grep -q "DOCUMENTS .* PROMPTS .* SYSTEMS .* CHECKLISTS" "$REFINED_DIR/$style/gumroad_cover.svg"; then
    fail "$style removed competing background headline"
  else
    pass "$style removed competing background headline"
  fi
done
check_file "$REFINED_DIR/index.html" "refined index exists"

PYTHONPATH=app python3 - <<PY
from pathlib import Path
from aesthetica import run_aesthetica_review

product_id = $PRODUCT_ID
report = run_aesthetica_review(product_id)
composition = report["composition"]
assert composition["composition_score"] >= 85, composition
assert composition["composition_overcrowded"] is False, composition
assert composition["launch_blocker"] is False, composition
assert composition["best_refined_variant"], composition
assert set(composition["refined_variants_reviewed"]) == {"minimal_enterprise", "modern_consulting", "premium_course"}, composition
assert "composition" in report, "AESTHETICA missing composition"
assert report["launch_ready"] is True, report["launch_ready"]

minimal = Path(f"products/product_{product_id}/marketplace_visuals/refined/minimal_enterprise/gumroad_cover.svg").read_text()
assert "HYDRA_LAYOUT_SAFETY: PASS" in minimal, "refined Gumroad layout did not pass"
assert "DOCUMENTS · PROMPTS · SYSTEMS · CHECKLISTS" not in minimal, "competing text still present"
print("composition", composition["composition_score"], composition["best_refined_variant"]["variant"])
PY
pass "AESTHETICA composition score and overcrowding blocker validate"

if [[ -d "products/product_${PRODUCT_ID}/marketplace_visuals/variants" ]]; then
  LIVE=0 bash scripts/verify_sprint281.sh >/tmp/hydra_sprint281_regression.out \
    && pass "Sprint 2.8.1 regression passes" || {
      cat /tmp/hydra_sprint281_regression.out || true
      fail "Sprint 2.8.1 regression passes"
    }
else
  pass "Sprint 2.8.1 regression skipped after final asset curation"
fi

if [[ "$failures" -eq 0 ]]; then
  echo "SPRINT 2.8.2 VERIFY: PASS"
else
  echo "SPRINT 2.8.2 VERIFY: FAIL ($failures)"
  exit 1
fi
