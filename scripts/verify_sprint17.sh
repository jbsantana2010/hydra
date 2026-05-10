#!/usr/bin/env bash
# verify_sprint17.sh — Sprint 1.7 Marketplace Intelligence v1
# Usage:
#   bash scripts/verify_sprint17.sh          # static checks only
#   LIVE=1 bash scripts/verify_sprint17.sh   # + live checks (running stack required)
set -euo pipefail

HYDRA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HYDRA_ROOT"

PASS=0; FAIL=0
BASE="${BASE:-http://localhost:8000}"
AUTH="${AUTH:--u ${HYDRA_BASIC_USER:-admin}:${HYDRA_BASIC_PASS:-change-me}}"

pass() { echo "PASS  $1"; PASS=$((PASS+1)); }
fail() { echo "FAIL  $1"; FAIL=$((FAIL+1)); }

echo "=== Sprint 1.7 — Static checks ==="

# ── Migration ────────────────────────────────────────────────────────────────
[ -f "app/alembic/versions/0003_sprint17_market_intelligence.py" ] \
  && pass "migration: 0003 file exists" \
  || fail "migration: 0003 file missing — expected app/alembic/versions/0003_sprint17_market_intelligence.py"

grep -q "market_research_runs" app/alembic/versions/0003_sprint17_market_intelligence.py \
  && pass "migration: creates market_research_runs" \
  || fail "migration: market_research_runs table missing from migration"

grep -q "market_research_items" app/alembic/versions/0003_sprint17_market_intelligence.py \
  && pass "migration: creates market_research_items" \
  || fail "migration: market_research_items table missing from migration"

grep -q "market_patterns" app/alembic/versions/0003_sprint17_market_intelligence.py \
  && pass "migration: creates market_patterns" \
  || fail "migration: market_patterns table missing from migration"

grep -q "down_revision.*\"0002\"\|down_revision.*'0002'" \
  app/alembic/versions/0003_sprint17_market_intelligence.py \
  && pass "migration: down_revision is 0002" \
  || fail "migration: wrong down_revision (expected 0002)"

grep -q "def downgrade" app/alembic/versions/0003_sprint17_market_intelligence.py \
  && pass "migration: downgrade() function present" \
  || fail "migration: downgrade() function missing"

# ── Models ───────────────────────────────────────────────────────────────────
grep -q "class MarketResearchRun" app/db.py \
  && pass "db.py: MarketResearchRun model present" \
  || fail "db.py: MarketResearchRun model missing"

grep -q "class MarketResearchItem" app/db.py \
  && pass "db.py: MarketResearchItem model present" \
  || fail "db.py: MarketResearchItem model missing"

grep -q "class MarketPattern" app/db.py \
  && pass "db.py: MarketPattern model present" \
  || fail "db.py: MarketPattern model missing"

grep -q "market_research_runs.*IF NOT EXISTS\|IF NOT EXISTS.*market_research_runs" app/db.py \
  && pass "db.py: market_research_runs safety net in _apply_one_shot_migrations" \
  || fail "db.py: market_research_runs safety net missing"

grep -q "market_patterns.*IF NOT EXISTS\|IF NOT EXISTS.*market_patterns" app/db.py \
  && pass "db.py: market_patterns safety net present" \
  || fail "db.py: market_patterns safety net missing"

# ── Routes ───────────────────────────────────────────────────────────────────
grep -q '"/market-research"' app/main.py \
  && pass "main.py: /market-research list route present" \
  || fail "main.py: /market-research list route missing"

grep -q 'import-csv\|import_csv' app/main.py \
  && pass "main.py: CSV import route present" \
  || fail "main.py: CSV import route missing"

grep -q 'market_pattern_extraction' app/main.py \
  && pass "main.py: analyze route uses market_pattern_extraction purpose" \
  || fail "main.py: market_pattern_extraction purpose string missing"

grep -q 'market_opportunity_generation' app/main.py \
  && pass "main.py: generate-opportunities uses market_opportunity_generation purpose" \
  || fail "main.py: market_opportunity_generation purpose string missing"

grep -q "source.*market_intelligence\|market_intelligence.*source" app/main.py \
  && pass "main.py: opportunities tagged source=market_intelligence" \
  || fail "main.py: source=market_intelligence tag missing"

grep -q "MarketResearchRun\|MarketResearchItem\|MarketPattern" app/main.py \
  && pass "main.py: new models imported" \
  || fail "main.py: new models not imported from db"

grep -q "import csv" app/main.py \
  && pass "main.py: import csv present" \
  || fail "main.py: import csv missing"

grep -q "import io" app/main.py \
  && pass "main.py: import io present" \
  || fail "main.py: import io missing"

grep -q "UploadFile\|uploadfile" app/main.py \
  && pass "main.py: UploadFile imported" \
  || fail "main.py: UploadFile not imported"

# ── Templates ────────────────────────────────────────────────────────────────
[ -f "app/templates/market_research_list.html" ] \
  && pass "templates: market_research_list.html exists" \
  || fail "templates: market_research_list.html missing"

[ -f "app/templates/market_research_detail.html" ] \
  && pass "templates: market_research_detail.html exists" \
  || fail "templates: market_research_detail.html missing"

grep -q 'import-csv\|import_csv' app/templates/market_research_detail.html \
  && pass "template: CSV import form in detail template" \
  || fail "template: CSV import form missing from detail template"

grep -q "Analyze\|analyze" app/templates/market_research_detail.html \
  && pass "template: Analyze button in detail template" \
  || fail "template: Analyze button missing from detail template"

grep -q "generate-opportunities\|Generate Opportunities" app/templates/market_research_detail.html \
  && pass "template: Generate Opportunities button in detail template" \
  || fail "template: Generate Opportunities button missing from detail template"

grep -q "market-research" app/templates/base.html \
  && pass "base.html: Market Research nav link present" \
  || fail "base.html: Market Research nav link missing"

# ── No forbidden external HTTP calls ────────────────────────────────────────
if grep -P "requests\.(get|post|put|delete)|httpx\.(get|post|put|delete)|aiohttp" app/main.py | \
   grep -qv "import httpx\|#"; then
  fail "main.py: contains raw external HTTP calls in route code — forbidden in Sprint 1.7"
else
  pass "main.py: no raw external HTTP calls in route code"
fi

# ── Sample CSV ───────────────────────────────────────────────────────────────
[ -f "scripts/sample_research.csv" ] \
  && pass "scripts: sample_research.csv exists" \
  || fail "scripts: sample_research.csv missing"

# ── Python syntax ────────────────────────────────────────────────────────────
python3 -m py_compile app/db.py   && pass "syntax: app/db.py OK"   || fail "syntax: app/db.py ERROR"
python3 -m py_compile app/main.py && pass "syntax: app/main.py OK" || fail "syntax: app/main.py ERROR"

echo ""
echo "=== Static: PASS=$PASS FAIL=$FAIL ==="
echo ""

if [ "${LIVE:-0}" != "1" ]; then
  echo "(Set LIVE=1 to run live checks)"
  exit $( [ "$FAIL" -eq 0 ] && echo 0 || echo 1 )
fi

echo "=== Sprint 1.7 — Live checks ==="

# Wait for server
for i in $(seq 1 10); do
  curl -sf "$BASE/health" >/dev/null 2>&1 && break
  echo "  waiting for server ($i/10)..."; sleep 2
done

# Create a run
resp=$(curl -si $AUTH \
  -d "label=Verify+Run+1.7&category=planners&query=planner&notes=automated+test" \
  "$BASE/market-research" --max-redirs 0 2>/dev/null || true)
http_code=$(echo "$resp" | grep -oP "^HTTP/\S+ \K\d+" | head -1 || echo "0")
location=$(echo "$resp" | grep -i "^Location:" | head -1 | tr -d '\r')
run_id=$(echo "$location" | grep -oP '(?<=/market-research/)\d+' | head -1 || echo "")

[ "$http_code" = "303" ] && [ -n "$run_id" ] \
  && pass "live: create run → 303 to /market-research/$run_id" \
  || fail "live: create run failed (http=$http_code location=$location)"

if [ -n "$run_id" ]; then
  # List page shows new run
  list_html=$(curl -sf $AUTH "$BASE/market-research" 2>/dev/null || echo "")
  echo "$list_html" | grep -qi "Verify Run 1.7" \
    && pass "live: list page shows new run" \
    || fail "live: list page missing new run"

  # Detail page renders
  detail_html=$(curl -sf $AUTH "$BASE/market-research/$run_id" 2>/dev/null || echo "")
  echo "$detail_html" | grep -qi "import\|Import\|CSV" \
    && pass "live: detail page renders with CSV import section" \
    || fail "live: detail page missing CSV import section"

  # CSV import
  CSV=$(mktemp /tmp/test_XXXX.csv)
  printf 'title,price,rating,review_count,tags,product_type\n' > "$CSV"
  printf '"ADHD Planner Bundle Printable",8.99,4.9,2341,"planner,adhd,focus",planner\n' >> "$CSV"
  printf '"Minimal Weekly Tracker",5.99,4.7,892,"tracker,weekly,minimal",tracker\n' >> "$CSV"
  printf '"Canva Social Kit for Coaches",19.99,4.8,445,"canva,social,coach",canva_template\n' >> "$CSV"

  import_resp=$(curl -si $AUTH \
    -F "file=@$CSV;type=text/csv" \
    "$BASE/market-research/$run_id/import-csv" --max-redirs 0 2>/dev/null || true)
  import_code=$(echo "$import_resp" | grep -oP "^HTTP/\S+ \K\d+" | head -1 || echo "0")
  import_loc=$(echo "$import_resp" | grep -i "^Location:" | head -1 | tr -d '\r')
  rm -f "$CSV"

  [ "$import_code" = "303" ] \
    && pass "live: CSV import → 303 redirect" \
    || fail "live: CSV import returned HTTP $import_code"

  echo "$import_loc" | grep -qi "success\|flash" \
    && pass "live: CSV import redirect has success flash" \
    || fail "live: CSV import redirect missing flash (location=$import_loc)"

  # Items appear on detail page
  detail_after=$(curl -sf $AUTH "$BASE/market-research/$run_id" 2>/dev/null || echo "")
  echo "$detail_after" | grep -qi "ADHD\|Planner\|Tracker\|Coach" \
    && pass "live: imported items visible on detail page" \
    || fail "live: imported items not visible on detail page"

  # Analyze (attempts LLM — check 303 regardless of LLM outcome)
  analyze_resp=$(curl -si $AUTH -d "" \
    "$BASE/market-research/$run_id/analyze" --max-redirs 0 2>/dev/null || true)
  analyze_code=$(echo "$analyze_resp" | grep -oP "^HTTP/\S+ \K\d+" | head -1 || echo "0")
  [ "$analyze_code" = "303" ] \
    && pass "live: analyze → 303 (LLM called or budget-blocked gracefully)" \
    || fail "live: analyze returned HTTP $analyze_code instead of 303"

  # Opportunities page still renders
  opps_resp=$(curl -si $AUTH "$BASE/opportunities" 2>/dev/null || true)
  opps_code=$(echo "$opps_resp" | grep -oP "^HTTP/\S+ \K\d+" | head -1 || echo "0")
  [ "$opps_code" = "200" ] \
    && pass "live: /opportunities page renders after run" \
    || fail "live: /opportunities page broken (http=$opps_code)"
fi

echo ""
echo "=== Final: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ] && echo "✅ All checks passed." || echo "❌ $FAIL check(s) failed."
exit $( [ "$FAIL" -eq 0 ] && echo 0 || echo 1 )
