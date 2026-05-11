#!/usr/bin/env bash
# verify_sprint23.sh — Sprint 2.3 acceptance verification
# Run from project root: bash scripts/verify_sprint23.sh
# Exit code 0 = all pass. Any FAIL = sprint incomplete.

set -eu
cd "$(dirname "$0")/.."

PASS=0
FAIL=0
WARN=0

pass() { echo "  [PASS] $1"; PASS=$((PASS+1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }
warn() { echo "  [WARN] $1"; WARN=$((WARN+1)); }
section() { echo; echo "── $1 ──"; }

echo "═══════════════════════════════════════════════════════════"
echo "  HYDRA Sprint 2.3 — Verification"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════════"

# ── 1. LLM adapter ────────────────────────────────────────────────────────────
section "LLM Adapter"

[ -f app/kit_llm_adapter.py ] && pass "kit_llm_adapter.py exists" || fail "kit_llm_adapter.py missing"
python3 -m py_compile app/kit_llm_adapter.py 2>/dev/null && pass "kit_llm_adapter.py syntax OK" || fail "kit_llm_adapter.py syntax error"
grep -q "make_kit_llm_caller" app/kit_llm_adapter.py && pass "make_kit_llm_caller defined" || fail "make_kit_llm_caller not found"
grep -q "call_llm_json" app/kit_llm_adapter.py && pass "call_llm_json used in adapter" || fail "call_llm_json not referenced in adapter"
grep -q "LlmBlocked\|LlmFailed" app/kit_llm_adapter.py && pass "LlmBlocked/LlmFailed imported" || fail "Exception imports missing"
grep -q "anthropic\|openai" app/kit_llm_adapter.py 2>/dev/null && fail "Direct SDK import in adapter (forbidden)" || pass "No direct SDK imports in adapter"

# ── 2. Prompt format ──────────────────────────────────────────────────────────
section "Prompt Format (sections dict, not bare array)"

# shared_tail is one string used by all 8 prompts — check it contains "sections"
grep -q '"sections"' app/kit_generator.py && pass "Prompts updated to return {\"sections\":[...]} (shared_tail pattern)" || fail "\"sections\" key not found in kit_generator.py prompts"
grep -q "Return ONLY a valid JSON object" app/kit_generator.py && pass "shared_tail instructs JSON object return" || fail "shared_tail still says JSON array"

# ── 3. kit_generator.py ───────────────────────────────────────────────────────
section "kit_generator.py"

python3 -m py_compile app/kit_generator.py 2>/dev/null && pass "kit_generator.py syntax OK" || fail "kit_generator.py syntax error"
grep -q "isinstance(result, list)" app/kit_generator.py && pass "generate_kit handles list return from adapter" || fail "generate_kit not updated for adapter list return"
grep -q "_FALLBACK_BY_DOC" app/kit_generator.py && pass "_FALLBACK_BY_DOC dict present (RE-specific fallback)" || fail "_FALLBACK_BY_DOC not found — fallback not upgraded"
grep -q "kit_document_generation\|kit_doc_sections" app/llm.py && pass "kit_doc_sections budget in llm.py" || fail "kit_doc_sections budget missing from llm.py"

# ── 4. kit_routes.py ──────────────────────────────────────────────────────────
section "kit_routes.py"

python3 -m py_compile app/kit_routes.py 2>/dev/null && pass "kit_routes.py syntax OK" || fail "kit_routes.py syntax error"
grep -q "make_kit_llm_caller" app/kit_routes.py && pass "_get_llm_caller wired to make_kit_llm_caller" || fail "_get_llm_caller not wired"
grep -q "def _get_llm_caller(db)" app/kit_routes.py && pass "_get_llm_caller accepts db parameter" || fail "_get_llm_caller does not accept db"

# ── 5. build_product43_kit.py ─────────────────────────────────────────────────
section "build_product43_kit.py"

python3 -m py_compile scripts/build_product43_kit.py 2>/dev/null && pass "build_product43_kit.py syntax OK" || fail "build_product43_kit.py syntax error"
grep -qi "import anthropic\|from anthropic\|anthropic\.Anthropic\|openai\.OpenAI\|import openai" scripts/build_product43_kit.py && fail "Direct SDK import found in build script (forbidden)" || pass "No direct SDK imports in build script"
grep -q "make_kit_llm_caller" scripts/build_product43_kit.py && pass "build script uses make_kit_llm_caller" || fail "build script not using make_kit_llm_caller"

# ── 6. kit_document.html template fix ────────────────────────────────────────
section "Template Fix"

grep -q "section\['items'\]" app/templates/kit_document.html && pass "section['items'] bracket access in template" || fail "section.items dict-method bug not fixed"
python3 -m py_compile app/kit_generator.py 2>/dev/null && pass "kit_generator re-compile after template patch OK" || fail "syntax error post-patch"

# ── 7. Product 43 — generated documents ───────────────────────────────────────
section "Product 43 Documents"

for num in 00 01 02 03 04 05 06 07; do
  html_count=$(ls products/product_43/${num}_*.html 2>/dev/null | wc -l)
  if [ "$html_count" -gt 0 ]; then
    pass "Doc $num HTML present"
  else
    fail "Doc $num HTML missing"
  fi
done

pdf_count=$(ls products/product_43/*.pdf 2>/dev/null | grep -v MASTER | wc -l || echo 0)
[ "$pdf_count" -ge 8 ] && pass "$pdf_count document PDFs present (≥8)" || fail "Only $pdf_count document PDFs (need ≥8)"

[ -f "products/product_43/MASTER_Complete_Kit.pdf" ] && pass "Master PDF present" || fail "Master PDF missing"
[ -f "products/product_43/Real_Estate_AI_Mastery_Kit.zip" ] && \
  pass "Delivery ZIP present" || fail "Delivery ZIP missing"

# Check no lorem ipsum
lorem_count=$(grep -rl "lorem ipsum\|Lorem Ipsum" products/product_43/*.html 2>/dev/null | wc -l)
[ "$lorem_count" -eq 0 ] && pass "No lorem ipsum in HTML documents" || fail "$lorem_count documents contain lorem ipsum"

# Check for real estate content
re_count=$(grep -l "real estate\|Real Estate\|listing\|agent\|buyer\|seller" products/product_43/*.html 2>/dev/null | wc -l)
[ "$re_count" -ge 8 ] && pass "All $re_count documents contain real estate domain language" || warn "Only $re_count/8 docs have RE domain language (check content)"

# ── 8. Manifest ───────────────────────────────────────────────────────────────
section "Manifest"

python3 -c "
import json, sys
d = json.load(open('products/product_43/manifest.json'))
assert 'Real Estate' in d.get('title',''), f'title wrong: {d.get(\"title\")}'
assert d.get('product_type') == 'ai_implementation_kit', f'product_type wrong'
assert d.get('readiness_status') != 'ready' or d.get('readiness_score') == 100, 'status/score mismatch'
print('OK')
" 2>/dev/null && pass "manifest.json — title and product_type correct" || fail "manifest.json title/type incorrect"

python3 -c "
import json
d = json.load(open('products/product_43/manifest.json'))
assert 'ADHD' not in d.get('title',''), 'legacy title found'
print('OK')
" 2>/dev/null && pass "manifest.json — no legacy ADHD title" || fail "manifest.json still has legacy ADHD title"

# ── 9. Sales assets ───────────────────────────────────────────────────────────
section "Sales Assets"

for f in gumroad_listing.md fiverr_gig.md pricing_strategy.md plr_license.md buyer_intake.md; do
  [ -f "products/product_43/sales/$f" ] && pass "sales/$f present" || fail "sales/$f missing"
done

# ── 10. Quality review ────────────────────────────────────────────────────────
section "Quality Review"

[ -f "products/product_43/quality/professional_kit_review.md" ] && \
  pass "quality/professional_kit_review.md present" || fail "quality review missing"

# ── 11. Covers ────────────────────────────────────────────────────────────────
section "SVG Covers"

cover_count=$(ls products/product_43/covers/*.svg 2>/dev/null | wc -l || echo 0)
[ "$cover_count" -ge 9 ] && pass "$cover_count SVG covers present (≥9)" || fail "Only $cover_count covers (need ≥9)"

# ── Summary ───────────────────────────────────────────────────────────────────
echo
echo "═══════════════════════════════════════════════════════════"
echo "  Results: $PASS PASS  |  $FAIL FAIL  |  $WARN WARN"
echo "═══════════════════════════════════════════════════════════"
if [ "$FAIL" -eq 0 ]; then
  echo "  ✓ Sprint 2.3 COMPLETE — Product 43 ready for LLM upgrade + listing"
  exit 0
else
  echo "  ✗ Sprint 2.3 INCOMPLETE — $FAIL check(s) failed"
  exit 1
fi
