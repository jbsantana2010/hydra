#!/usr/bin/env bash
# Focused Sprint 2.3 check: Product 43 kit output + persisted kit_doc_sections rows.

set -eu
cd "$(dirname "$0")/.."

PASS=0
FAIL=0
WARN=0

pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  [WARN] $1"; WARN=$((WARN + 1)); }

PRODUCT_DIR="products/product_43"
REPORT="$PRODUCT_DIR/kit_generation_report.json"

echo "HYDRA Sprint 2.3 — LLM persistence verification"

if grep -R -q -E "CONTENT PENDING|LLM generation was not available" "$PRODUCT_DIR"/*.html 2>/dev/null; then
  fail "Fallback placeholder text found in Product 43 HTML"
else
  pass "No fallback placeholder text in Product 43 HTML"
fi

html_count=$(find "$PRODUCT_DIR" -maxdepth 1 -name '*.html' | wc -l)
[ "$html_count" -ge 8 ] && pass "$html_count HTML documents present" || fail "Only $html_count HTML documents present"

pdf_count=$(find "$PRODUCT_DIR" -maxdepth 1 -name '*.pdf' ! -name 'MASTER_*' | wc -l)
[ "$pdf_count" -ge 8 ] && pass "$pdf_count individual PDFs present" || fail "Only $pdf_count individual PDFs present"

[ -f "$PRODUCT_DIR/MASTER_Complete_Kit.pdf" ] && pass "Master PDF present" || fail "Master PDF missing"

zip_count=$(find "$PRODUCT_DIR" -maxdepth 1 -name '*.zip' | wc -l)
[ "$zip_count" -ge 1 ] && pass "$zip_count delivery ZIP file(s) present" || fail "Delivery ZIP missing"

if [ -f "$REPORT" ]; then
  python3 - "$REPORT" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path, encoding="utf-8"))
assert data.get("llm_used") is True, data
assert data.get("fallback_used") is False, data
assert len(data.get("llm_documents", [])) == 8, data
assert not data.get("fallback_documents"), data
assert not data.get("failed_documents"), data
PY
  pass "kit_generation_report.json confirms all-LLM generation"
else
  fail "kit_generation_report.json missing"
fi

if command -v docker >/dev/null 2>&1 && docker compose ps >/dev/null 2>&1; then
  count=$(docker compose exec -T postgres psql -U hydra -d hydra -Atc \
    "select count(*) from llm_calls where purpose='kit_doc_sections' and created_at >= now() - interval '24 hours';" 2>/dev/null || echo 0)
  case "$count" in
    ''|*[!0-9]*) warn "Could not parse kit_doc_sections count: $count" ;;
    *)
      [ "$count" -ge 8 ] && pass "$count kit_doc_sections rows persisted in llm_calls" || fail "Only $count kit_doc_sections rows persisted in llm_calls"
      ;;
  esac
else
  warn "Docker unavailable; skipped llm_calls DB check"
fi

echo
echo "Results: $PASS PASS | $FAIL FAIL | $WARN WARN"
[ "$FAIL" -eq 0 ]
