#!/usr/bin/env bash
# Sprint 1.5 — In-process Agentic Generation verification.
# Tests all five generation routes: outline, content, listing, qa, distribution.
# Safe to run without API keys — guard paths are the primary local verification.
set +e

AUTH="${HYDRA_BASIC_USER:-admin}:${HYDRA_BASIC_PASS:-change-me}"
B="http://localhost:8000"
cd /home/jb/dev/hydra || exit 1

FAIL=0
pass() { echo "  PASS — $1"; }
fail() { echo "  FAIL — $1"; FAIL=1; }
header() { echo; echo "=== $1 ==="; }

sql() {
  docker compose exec -T postgres psql -U "${POSTGRES_USER:-hydra}" -d "${POSTGRES_DB:-hydra}" -tA -c "$1"
}

restore_flags() {
  curl -sS -u "$AUTH" -X POST -F "enabled=false" "$B/settings/kill-switch" >/dev/null 2>&1
  curl -sS -u "$AUTH" -X POST -F "daily_budget_usd=3" "$B/settings/budget" >/dev/null 2>&1
}
trap restore_flags EXIT

header "sprint 1.5 imports"
docker compose exec -T hydra-console python - <<'PY'
from main import (
    generate_outline, generate_content, generate_listing,
    generate_qa, generate_distribution,
    _latest_artifact, _artifact_context, _generation_error,
)
from llm import call_llm_json
import inspect
sig = inspect.signature(call_llm_json)
assert "reverse_providers" in sig.parameters, "reverse_providers not in call_llm_json"
print("imports ok")
PY
[ "$?" = "0" ] && pass "sprint 1.5 imports + reverse_providers param" || fail "imports failed"

header "health check"
curl -fsS "$B/health" >/dev/null && pass "/health 200" || fail "/health failed"

header "create test candidate and product for generation"
CID=$(sql "INSERT INTO opportunity_candidates (source, topic, vertical, production_format, demand_velocity, monetization_fit, ai_exploitability, cross_source_confirmation, time_to_revenue, saturation_penalty, platform_risk_penalty, score, evidence) VALUES ('Sprint15 Verify', 'AI Meeting Note Cleanup Kit for Solo Consultants', 'creator economy tools', 'prompt pack + workflow PDF', 88, 82, 90, 70, 86, 25, 15, 74, 'Consultants spend 30 min cleaning AI meeting summaries. Prompt pack solves this.') RETURNING id")
CID=$(echo "$CID" | grep -E '^[0-9]+$' | head -1 | tr -d '[:space:]')
[ -n "$CID" ] && pass "test candidate created (id=$CID)" || { fail "could not create candidate"; exit 1; }

REDIRECT=$(curl -sS -u "$AUTH" -X POST -i "$B/opportunities/$CID/approve" | tr -d '\r' | awk -F': ' 'tolower($1)=="location"{print $2}' | head -1)
PID=$(echo "$REDIRECT" | grep -oE '[0-9]+' | head -1)
[ -n "$PID" ] && pass "product created (id=$PID)" || { fail "approval did not create product"; exit 1; }


header "kill switch blocks all five generation routes"
curl -sS -u "$AUTH" -X POST -F "enabled=true" "$B/settings/kill-switch" >/dev/null
for step in outline content listing qa distribution; do
  RESP=$(curl -sS -u "$AUTH" -X POST "$B/products/$PID/generate/$step")
  echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status'] in ('blocked','missing_prereq'), d" 2>/dev/null \
    && pass "kill switch blocks generate/$step" \
    || fail "generate/$step not blocked by kill switch"
done
curl -sS -u "$AUTH" -X POST -F "enabled=false" "$B/settings/kill-switch" >/dev/null

header "budget=0 blocks generation routes (after kill switch off)"
curl -sS -u "$AUTH" -X POST -F "daily_budget_usd=0" "$B/settings/budget" >/dev/null
for step in outline content listing qa distribution; do
  RESP=$(curl -sS -u "$AUTH" -X POST "$B/products/$PID/generate/$step")
  echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status'] in ('blocked','missing_prereq'), d" 2>/dev/null \
    && pass "budget=0 blocks generate/$step" \
    || fail "generate/$step not blocked by budget=0"
done
curl -sS -u "$AUTH" -X POST -F "daily_budget_usd=3" "$B/settings/budget" >/dev/null

header "prerequisite gates (no keys, budget restored)"
# With no API keys and budget=3, outline will fail (LlmBlocked: no key).
# content/listing/qa/distribution must return missing_prereq since outline artifact doesn't exist.
RESP=$(curl -sS -u "$AUTH" -X POST "$B/products/$PID/generate/content")
echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='missing_prereq', d" 2>/dev/null \
  && pass "content prerequisite gate (no outline)" \
  || fail "content prerequisite gate failed"

RESP=$(curl -sS -u "$AUTH" -X POST "$B/products/$PID/generate/listing")
echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='missing_prereq', d" 2>/dev/null \
  && pass "listing prerequisite gate (no content)" \
  || fail "listing prerequisite gate failed"

RESP=$(curl -sS -u "$AUTH" -X POST "$B/products/$PID/generate/qa")
echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='missing_prereq', d" 2>/dev/null \
  && pass "qa prerequisite gate (no content)" \
  || fail "qa prerequisite gate failed"

RESP=$(curl -sS -u "$AUTH" -X POST "$B/products/$PID/generate/distribution")
echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='missing_prereq', d" 2>/dev/null \
  && pass "distribution prerequisite gate (no listing)" \
  || fail "distribution prerequisite gate failed"


header "no-key fallback: outline returns blocked (not 500)"
RESP=$(curl -sS -u "$AUTH" -X POST "$B/products/$PID/generate/outline")
echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status'] in ('blocked','failed'), d" 2>/dev/null \
  && pass "outline returns blocked/failed without API keys (no crash)" \
  || fail "outline crashed without API keys"

header "product_edit renders with generation_status"
curl -fsS -u "$AUTH" "$B/products/$PID/edit" -o /tmp/hydra_edit_15.html
grep -q "Generate Outline" /tmp/hydra_edit_15.html && pass "product_edit shows Generate Outline button" || fail "Generate Outline button missing"
grep -q "Generate Content" /tmp/hydra_edit_15.html && pass "product_edit shows Generate Content button" || fail "Generate Content button missing"
grep -q "Generate Listing Copy" /tmp/hydra_edit_15.html && pass "product_edit shows Generate Listing Copy button" || fail "Generate Listing Copy button missing"
grep -q "Run QA Review" /tmp/hydra_edit_15.html && pass "product_edit shows Run QA Review button" || fail "Run QA Review button missing"
grep -q "Generate Distribution Posts" /tmp/hydra_edit_15.html && pass "product_edit shows Generate Distribution Posts button" || fail "Generate Distribution Posts button missing"
grep -q "Gumroad.*Etsy.*Sellfy.*Payhip" /tmp/hydra_edit_15.html && pass "product_edit shows all four storefronts" || fail "storefronts not listed"

header "existing routes unbroken"
curl -fsS -u "$AUTH" "$B/products" >/dev/null && pass "/products renders" || fail "/products failed"
curl -fsS -u "$AUTH" "$B/revenue" >/dev/null && pass "/revenue renders" || fail "/revenue failed"
curl -fsS -u "$AUTH" "$B/launch" >/dev/null && pass "/launch renders" || fail "/launch failed"
curl -fsS -u "$AUTH" "$B/settings" >/dev/null && pass "/settings renders" || fail "/settings failed"

if [ -n "${ANTHROPIC_API_KEY:-}" ] || [ -n "${OPENAI_API_KEY:-}" ]; then
  header "optional real API-key smoke: full generation pipeline"
  echo "  Running outline generation with real API key..."
  HTTP_CODE=$(curl -sS -u "$AUTH" -X POST -o /dev/null -w "%{http_code}" "$B/products/$PID/generate/outline")
  [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "303" ] && pass "outline returned $HTTP_CODE" || fail "outline HTTP $HTTP_CODE"

  ART_COUNT=$(sql "SELECT count(*) FROM product_artifacts WHERE product_id=$PID AND artifact_type='outline'")
  [ "${ART_COUNT:-0}" -ge 1 ] && pass "outline artifact saved to DB" || fail "outline artifact not in DB"

  # If outline succeeded, try content
  if [ "${ART_COUNT:-0}" -ge 1 ]; then
    HTTP_CODE=$(curl -sS -u "$AUTH" -X POST -o /dev/null -w "%{http_code}" "$B/products/$PID/generate/content")
    [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "303" ] && pass "content returned $HTTP_CODE" || fail "content HTTP $HTTP_CODE"
  fi
else
  echo "  SKIP — no API keys configured; guard-path verification is the required local check"
fi

echo
if [ "$FAIL" = "0" ]; then
  echo "VERIFY_SPRINT15 — PASS"
  exit 0
fi
echo "VERIFY_SPRINT15 — FAIL"
exit 1
