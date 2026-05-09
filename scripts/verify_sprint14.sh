#!/usr/bin/env bash
# Sprint 1.4 — Controlled LLM Execution Layer verification.
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
  curl -sS -u "$AUTH" -X POST -F "enabled=false" "$B/settings/kill-switch" >/dev/null
  curl -sS -u "$AUTH" -X POST -F "daily_budget_usd=3" "$B/settings/budget" >/dev/null
}
trap restore_flags EXIT

header "app imports"
docker compose exec -T hydra-console python - <<'PY'
from main import app, _hn_classify, build_default_product_fields
from llm import call_llm_json, LlmBlocked, LlmFailed, get_today_llm_spend
from db import LlmCall
print("imports ok")
PY
[ "$?" = "0" ] && pass "main/llm/db imports" || fail "imports failed"

header "schema"
COLS=$(sql "SELECT column_name FROM information_schema.columns WHERE table_name='llm_calls' ORDER BY column_name")
for col in id provider model purpose prompt_tokens completion_tokens cost_usd duration_ms status error created_at; do
  echo "$COLS" | grep -qx "$col" && pass "llm_calls.$col" || fail "missing llm_calls.$col"
done

header "health and settings"
curl -fsS "$B/health" >/dev/null && pass "/health 200" || fail "/health failed"
curl -fsS -u "$AUTH" "$B/settings" -o /tmp/hydra_settings.html
grep -q "Today's LLM spend" /tmp/hydra_settings.html && pass "settings shows LLM spend" || fail "settings missing LLM spend"
grep -q "Recent LLM Calls" /tmp/hydra_settings.html && pass "settings shows recent calls" || fail "settings missing recent calls"

header "direct LLM guard paths"
BEFORE=$(sql "SELECT count(*) FROM llm_calls")
curl -fsS -u "$AUTH" -X POST -F "enabled=true" "$B/settings/kill-switch" >/dev/null
docker compose exec -T hydra-console python - <<'PY'
from db import session_scope
from llm import call_llm_json, LlmBlocked

with session_scope() as db:
    try:
        call_llm_json(db, "verify_kill_switch", "Return JSON.", "Return {\"ok\": true}", {"ok": True}, max_cost_usd=0.0005)
    except LlmBlocked as exc:
        print("blocked", exc)
    else:
        raise SystemExit("expected LlmBlocked")
PY
[ "$?" = "0" ] && pass "kill switch blocks llm_call" || fail "kill switch did not block"
curl -fsS -u "$AUTH" -X POST -F "enabled=false" "$B/settings/kill-switch" >/dev/null

curl -fsS -u "$AUTH" -X POST -F "daily_budget_usd=0" "$B/settings/budget" >/dev/null
docker compose exec -T hydra-console python - <<'PY'
from db import session_scope
from llm import call_llm_json, LlmBlocked

with session_scope() as db:
    try:
        call_llm_json(db, "verify_budget_zero", "Return JSON.", "Return {\"ok\": true}", {"ok": True}, max_cost_usd=0.0005)
    except LlmBlocked as exc:
        print("blocked", exc)
    else:
        raise SystemExit("expected LlmBlocked")
PY
[ "$?" = "0" ] && pass "daily_budget_usd=0 blocks llm_call" || fail "budget zero did not block"
curl -fsS -u "$AUTH" -X POST -F "daily_budget_usd=3" "$B/settings/budget" >/dev/null

AFTER=$(sql "SELECT count(*) FROM llm_calls")
[ "$AFTER" -gt "$BEFORE" ] && pass "blocked attempts logged llm_calls rows" || fail "llm_calls rows not logged"

if [ -n "${ANTHROPIC_API_KEY:-}" ] || [ -n "${OPENAI_API_KEY:-}" ]; then
  header "optional real API-key smoke"
  docker compose exec -T hydra-console python - <<'PY'
from db import session_scope
from llm import call_llm_json

with session_scope() as db:
    out = call_llm_json(db, "verify_real_call", "Return JSON only.", "Return {\"ok\": true}.", {"ok": True}, max_cost_usd=0.01)
    assert out.get("ok") is True
print("real call ok")
PY
  [ "$?" = "0" ] && pass "real LLM call returned JSON" || fail "real LLM call failed"
else
  echo "  SKIP — no API keys configured; fallback behavior is the required local verification"
fi

header "HN classifier and fallback"
docker compose exec -T hydra-console python - <<'PY' >/tmp/hydra_hn_classify.out
from main import _hn_classify, _hn_to_candidate

v, f = _hn_classify("Show HN: cline-style AI coding agent for Cursor")
assert v == "AI coding tools", (v, f)
assert f == "cheat sheet PDF", (v, f)
candidate = _hn_to_candidate({
    "title": "Show HN: Safe sandbox workflow for AI coding agents",
    "points": 42,
    "num_comments": 12,
    "url": "https://example.com",
    "created_at": "2026-05-09T00:00:00Z",
})
assert candidate["source"] == "HackerNews"
assert candidate["vertical"]
assert candidate["production_format"]
assert candidate["score"] >= 0
print(candidate["vertical"])
print(candidate["production_format"])
PY
[ "$?" = "0" ] && pass "HN classifier returns valid candidate fallback" || fail "HN classifier fallback failed"

header "HN collection no-crash fallback"
RESP=$(curl -fsS -u "$AUTH" -X POST -F "query=AI coding agent" "$B/opportunities/collect/hn")
echo "  response: $RESP"
echo "$RESP" | grep -q '"source":"HackerNews"' && pass "HN collection returned JSON" || fail "HN collection failed"

header "approval still creates draft product"
CID=$(sql "INSERT INTO opportunity_candidates (source, topic, vertical, production_format, demand_velocity, monetization_fit, ai_exploitability, cross_source_confirmation, time_to_revenue, saturation_penalty, platform_risk_penalty, score, evidence) VALUES ('Sprint14 Verify', 'Sprint 1.4 Safe AI Coding Workflow', 'AI coding tools', 'cheat sheet PDF', 80, 80, 80, 40, 80, 20, 10, 72, 'verification candidate') RETURNING id")
CID=$(echo "$CID" | grep -E '^[0-9]+$' | head -1 | tr -d '[:space:]')
if [ -z "$CID" ]; then
  fail "could not create verification candidate"
else
  echo "  approving candidate $CID"
fi
REDIRECT=$(curl -sS -u "$AUTH" -X POST -i "$B/opportunities/$CID/approve" | tr -d '\r' | awk -F': ' 'tolower($1)=="location" {print $2}' | head -1)
PID=$(echo "$REDIRECT" | grep -oE '[0-9]+' | head -1)
if [ -n "$PID" ]; then
  STATUS=$(sql "SELECT status FROM products WHERE id=$PID")
  NOTES=$(sql "SELECT notes FROM products WHERE id=$PID")
  echo "$STATUS" | grep -qx "draft" && pass "approval created draft product $PID" || fail "approved product not draft"
  echo "$NOTES" | grep -q "Suggested deliverable structure\\|LLM-assisted draft notes" && pass "product notes populated" || fail "product notes missing"
else
  fail "approval redirect missing product id"
fi

header "no route crashes without API keys"
curl -fsS -u "$AUTH" "$B/products" >/dev/null && pass "/products renders" || fail "/products failed"
curl -fsS -u "$AUTH" "$B/revenue" >/dev/null && pass "/revenue renders" || fail "/revenue failed"
curl -fsS -u "$AUTH" "$B/launch" >/dev/null && pass "/launch renders" || fail "/launch failed"

echo
if [ "$FAIL" = "0" ]; then
  echo "VERIFY_SPRINT14 — PASS"
  exit 0
fi

echo "VERIFY_SPRINT14 — FAIL"
exit 1
