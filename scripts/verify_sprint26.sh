#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LIVE="${LIVE:-0}"
PRODUCT_ID="${PRODUCT_ID:-43}"
failures=0

pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1"; failures=$((failures + 1)); }
check_file() { [[ -f "$1" ]] && pass "$2" || fail "$2"; }
check_dir() { [[ -d "$1" ]] && pass "$2" || fail "$2"; }
check_grep() { grep -q "$1" "$2" && pass "$3" || fail "$3"; }

check_dir agents "agents folder exists"
check_file agents/AESTHETICA.md "AESTHETICA spec exists"
check_file agents/HERMES_FOUNDATION.md "Hermes foundation spec exists"
check_file agents/agent_registry.json "agent registry exists"
check_file app/aesthetica.py "AESTHETICA scoring module exists"
check_grep "aesthetica-review" app/main.py "AESTHETICA route exists"
check_grep "Run AESTHETICA Review" app/templates/product_edit.html "product edit template has review button"
check_grep "spacing/collision risk" agents/AESTHETICA.md "scoring dimensions documented"

python3 -m py_compile app/aesthetica.py app/main.py || fail "Python compile failed"

PYTHONPATH=app python3 - <<PY
from aesthetica import run_aesthetica_review
report = run_aesthetica_review($PRODUCT_ID)
assert report["variant_reviews"], "no variants reviewed"
assert report["best_gumroad_theme"], "no Gumroad recommendation"
assert report["best_fiverr_theme"], "no Fiverr recommendation"
assert report["output_paths"]["hermes_latest"].endswith("latest.json")
print("generated", report["overall_score"], report["best_gumroad_theme"]["theme_name"])
PY
pass "AESTHETICA review generation completed"

QUALITY_DIR="products/product_${PRODUCT_ID}/quality"
AGENT_DIR="products/product_${PRODUCT_ID}/agent_reviews/aesthetica"
check_file "$QUALITY_DIR/aesthetica_review.json" "quality JSON generated"
check_file "$QUALITY_DIR/aesthetica_review.md" "quality markdown generated"
check_file "$AGENT_DIR/latest.json" "Hermes-readable latest JSON generated"
check_grep "variant_reviews" "$QUALITY_DIR/aesthetica_review.json" "Product ${PRODUCT_ID} variants reviewed"
check_grep "best_gumroad_theme" "$AGENT_DIR/latest.json" "Hermes JSON includes Gumroad recommendation"

if [[ "$LIVE" == "1" ]]; then
  code="$(curl -sS -u "${HYDRA_BASIC_USER:-admin}:${HYDRA_BASIC_PASS:-change-me}" \
    -X POST -o /tmp/hydra_sprint26_route.out -w "%{http_code}" \
    "http://localhost:8000/products/${PRODUCT_ID}/aesthetica-review" || true)"
  if [[ "$code" == "303" || "$code" == "200" ]]; then
    pass "live AESTHETICA route responds"
  else
    cat /tmp/hydra_sprint26_route.out || true
    fail "live AESTHETICA route responds (HTTP $code)"
  fi

  page_code="$(curl -sS -u "${HYDRA_BASIC_USER:-admin}:${HYDRA_BASIC_PASS:-change-me}" \
    -o /tmp/hydra_sprint26_product.out -w "%{http_code}" \
    "http://localhost:8000/products/${PRODUCT_ID}/edit" || true)"
  if [[ "$page_code" == "200" ]] && grep -q "AESTHETICA Visual Review" /tmp/hydra_sprint26_product.out; then
    pass "product edit UI renders AESTHETICA section"
  else
    fail "product edit UI renders AESTHETICA section"
  fi
else
  pass "LIVE checks skipped"
fi

if [[ -f scripts/verify_sprint25.sh ]]; then
  LIVE=0 bash scripts/verify_sprint25.sh >/tmp/hydra_sprint25_regression.out && pass "Sprint 2.5 regression passes" || {
    cat /tmp/hydra_sprint25_regression.out
    fail "Sprint 2.5 regression passes"
  }
else
  fail "Sprint 2.5 regression script exists"
fi

if [[ "$failures" -eq 0 ]]; then
  echo "SPRINT 2.6 VERIFY: PASS"
else
  echo "SPRINT 2.6 VERIFY: FAIL ($failures)"
  exit 1
fi
