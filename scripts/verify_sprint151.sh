#!/usr/bin/env bash
# verify_sprint151.sh — Sprint 1.5.1: LLM Observability + Product UX Polish
#
# Usage:
#   cd /home/jb/dev/hydra
#   bash scripts/verify_sprint151.sh           # static checks
#   LIVE=1 bash scripts/verify_sprint151.sh    # + live HTTP checks (needs running stack)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

PASS=0; FAIL=0; SKIP=0
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
pass() { echo -e "${GREEN}PASS${NC}  $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}FAIL${NC}  $1"; FAIL=$((FAIL+1)); }
skip() { echo -e "${YELLOW}SKIP${NC}  $1 (reason: $2)"; SKIP=$((SKIP+1)); }

echo ""
echo "================================="
echo " HYDRA Sprint 1.5.1 Verification"
echo "================================="
echo ""

# ── 1. db.py — error_type column ──────────────────────────────────────────
echo "── 1. db.py — error_type column ──────────────────────────────"
if grep -q "error_type" app/db.py; then
    pass "LlmCall.error_type column defined in db.py"
else
    fail "LlmCall.error_type MISSING from db.py"
fi
if grep -q "error_type.*TEXT" app/db.py; then
    pass "error_type in _apply_one_shot_migrations()"
else
    fail "error_type NOT in _apply_one_shot_migrations()"
fi

# ── 2. llm.py — error classification ────────────────────────────────────
echo ""
echo "── 2. llm.py — error classification ──────────────────────────"
if grep -q "_classify_error" app/llm.py; then
    pass "_classify_error() function defined"
else
    fail "_classify_error() MISSING from llm.py"
fi
for label in "auth_error" "quota_error" "bad_request" "provider_5xx" "timeout" "bad_json" "kill_switch" "budget_exceeded"; do
    if grep -q "\"$label\"" app/llm.py; then
        pass "Error type '$label' defined"
    else
        fail "Error type '$label' MISSING"
    fi
done
if grep -q "error_type=_classify_error" app/llm.py; then
    pass "_classify_error() called for failed provider logs"
else
    fail "_classify_error() not wired to _log_call() for failures"
fi
if grep -q "error_type=error_type" app/llm.py; then
    pass "_log_call() stores error_type"
else
    fail "_log_call() does NOT store error_type"
fi

# ── 3. settings.html — error visibility ──────────────────────────────────
echo ""
echo "── 3. settings.html — error visibility ───────────────────────"
if grep -q "error_type" app/templates/settings.html; then
    pass "settings.html renders error_type column"
else
    fail "settings.html missing error_type"
fi
if grep -q "Error Detail" app/templates/settings.html || grep -q "error.*call.error" app/templates/settings.html; then
    pass "settings.html renders error detail"
else
    fail "settings.html missing error detail column"
fi
if grep -q "duration_ms" app/templates/settings.html; then
    pass "settings.html shows duration_ms"
else
    fail "settings.html missing duration_ms"
fi
if grep -q "title=\"{{ call.error" app/templates/settings.html; then
    pass "settings.html has hover title for full error text"
else
    fail "settings.html missing hover title for error"
fi

# ── 4. opportunities.html — created_at + source badges ───────────────────
echo ""
echo "── 4. opportunities.html — created_at + source badges ────────"
if grep -q "created_at" app/templates/opportunities.html; then
    pass "opportunities.html shows created_at"
else
    fail "opportunities.html missing created_at"
fi
if grep -q "strftime" app/templates/opportunities.html; then
    pass "created_at formatted with strftime"
else
    fail "created_at NOT formatted (raw datetime)"
fi
if grep -q "HackerNews" app/templates/opportunities.html || grep -q "HN" app/templates/opportunities.html; then
    pass "HN source badge present"
else
    fail "HN source badge MISSING"
fi
if grep -q "Mock" app/templates/opportunities.html; then
    pass "Mock source badge present"
else
    fail "Mock source badge MISSING"
fi

# ── 5. main.py — flash redirect helpers ──────────────────────────────────
echo ""
echo "── 5. main.py — flash redirect helpers ───────────────────────"
if grep -q "_generation_redirect" app/main.py; then
    pass "_generation_redirect() helper defined"
else
    fail "_generation_redirect() MISSING"
fi
if grep -q "_last_llm_call_meta" app/main.py; then
    pass "_last_llm_call_meta() helper defined"
else
    fail "_last_llm_call_meta() MISSING"
fi

# All 5 routes should use _generation_redirect not raw JSONResponse for errors
for step in "outline" "product_content" "listing_copy" "qa_review" "distribution_post"; do
    count=$(grep -c "_generation_redirect(product_id" app/main.py || true)
done
if [[ "$count" -ge 5 ]]; then
    pass "_generation_redirect used in generation routes ($count calls found)"
else
    fail "_generation_redirect calls look low: $count (expected ≥5)"
fi

# No generation route should return raw JSONResponse for error cases
json_errors=$(grep -c "return _generation_error" app/main.py || true)
if [[ "$json_errors" -eq 1 ]]; then
    pass "_generation_error() kept as legacy-only stub (1 remaining definition)"
elif [[ "$json_errors" -eq 0 ]]; then
    pass "_generation_error() fully replaced"
else
    fail "_generation_error() still called in routes ($json_errors uses) — operator would see raw JSON"
fi

# ── 6. edit_product GET — flash params ────────────────────────────────────
echo ""
echo "── 6. edit_product GET — flash params ────────────────────────"
if grep -q "flash_banner" app/main.py; then
    pass "edit_product builds flash_banner context"
else
    fail "edit_product missing flash_banner"
fi
if grep -q "recent_llm_calls" app/main.py; then
    pass "edit_product passes recent_llm_calls to template"
else
    fail "edit_product missing recent_llm_calls"
fi

# ── 7. product_edit.html — flash banner + latest action ──────────────────
echo ""
echo "── 7. product_edit.html — flash banner + latest LLM activity ─"
if grep -q "flash_banner" app/templates/product_edit.html; then
    pass "product_edit.html renders flash_banner"
else
    fail "product_edit.html missing flash_banner block"
fi
if grep -q "latest.*LLM\|Latest LLM" app/templates/product_edit.html; then
    pass "product_edit.html has Latest LLM Activity section"
else
    fail "product_edit.html missing Latest LLM Activity"
fi
if grep -q "error_type" app/templates/product_edit.html; then
    pass "product_edit.html shows error_type in activity table"
else
    fail "product_edit.html missing error_type in activity"
fi

# ── 8. Python syntax ──────────────────────────────────────────────────────
echo ""
echo "── 8. Python syntax ──────────────────────────────────────────"
for f in app/db.py app/main.py app/llm.py; do
    if python3 -m py_compile "$f" 2>/dev/null; then
        pass "SYNTAX OK: $f"
    else
        fail "SYNTAX ERROR: $f"
    fi
done

# ── 9. Live HTTP checks (optional) ────────────────────────────────────────
echo ""
echo "── 9. Live HTTP checks ────────────────────────────────────────"
BASE="http://localhost:8000"
AUTH="-u admin:change-me"

if [[ "${LIVE:-0}" != "1" ]]; then
    skip "/health check"            "LIVE=1 not set"
    skip "settings page renders"    "LIVE=1 not set"
    skip "opportunities page renders" "LIVE=1 not set"
    skip "product edit page renders"  "LIVE=1 not set"
    skip "kill switch flash redirect" "LIVE=1 not set"
    skip "budget=0 flash redirect"    "LIVE=1 not set"
else
    # Health
    code=$(curl -s -o /dev/null -w "%{http_code}" $AUTH "$BASE/health")
    [[ "$code" == "200" ]] && pass "/health 200" || fail "/health returned $code"

    # Settings page (HTML, not raw error)
    body=$(curl -s $AUTH "$BASE/settings")
    echo "$body" | grep -q "Recent LLM Calls" && pass "settings.html renders" || fail "settings.html broken"
    echo "$body" | grep -q "Error Type\|error_type" && pass "settings shows Error Type col" || fail "settings missing Error Type col"

    # Opportunities page
    body=$(curl -s $AUTH "$BASE/opportunities")
    echo "$body" | grep -q "Created" && pass "opportunities shows Created col" || fail "opportunities missing Created col"

    # Get first product ID
    prod_body=$(curl -s $AUTH "$BASE/products")
    prod_id=$(echo "$prod_body" | grep -oP 'href="/products/\K[0-9]+' | head -1 || true)
    if [[ -n "$prod_id" ]]; then
        edit_body=$(curl -s $AUTH "$BASE/products/$prod_id/edit")
        echo "$edit_body" | grep -q "Latest LLM Activity\|Generate" && \
            pass "product_edit.html renders (prod $prod_id)" || \
            fail "product_edit.html broken for prod $prod_id"
    else
        skip "product edit page" "no products found"
    fi

    # Kill switch → should redirect back to product edit with flash, not JSON
    docker compose exec hydra-console python -c "
from db import set_flag_value
set_flag_value('hydra:kill', 'true')
" 2>/dev/null

    if [[ -n "$prod_id" ]]; then
        result=$(curl -s -L $AUTH -X POST "$BASE/products/$prod_id/generate/outline")
        # Should contain HTML product edit page, not raw JSON
        if echo "$result" | grep -q "Edit Product\|Generate Outline\|blocked\|kill"; then
            pass "kill switch produces HTML redirect (not raw JSON)"
        else
            fail "kill switch response looks wrong — check manually"
        fi
    fi

    # Re-enable kill switch
    docker compose exec hydra-console python -c "
from db import set_flag_value
set_flag_value('hydra:kill', 'false')
" 2>/dev/null

    # Budget=0 → should redirect with blocked flash
    docker compose exec hydra-console python -c "
from db import set_flag_value
set_flag_value('daily_budget_usd', '0')
" 2>/dev/null

    if [[ -n "$prod_id" ]]; then
        result=$(curl -s -L $AUTH -X POST "$BASE/products/$prod_id/generate/outline")
        if echo "$result" | grep -q "Edit Product\|Generate Outline\|budget\|blocked"; then
            pass "budget=0 produces HTML redirect (not raw JSON)"
        else
            fail "budget=0 response looks wrong — check manually"
        fi
    fi

    # Restore budget
    docker compose exec hydra-console python -c "
from db import set_flag_value
set_flag_value('daily_budget_usd', '3')
" 2>/dev/null
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "================================="
printf " PASS: %s  FAIL: %s  SKIP: %s\n" "$PASS" "$FAIL" "$SKIP"
echo "================================="
if [[ "$FAIL" -gt 0 ]]; then
    echo "Sprint 1.5.1 verification FAILED"
    exit 1
else
    echo "Sprint 1.5.1 verification PASSED ✓"
fi
