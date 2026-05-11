#!/usr/bin/env bash
# HYDRA Sprint 2.1 verification — Package Quality Scoring + Upload Readiness
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0
BASE="${BASE:-http://localhost:8000}"
AUTH_USER="${HYDRA_BASIC_USER:-admin}"
AUTH_PASS="${HYDRA_BASIC_PASS:-change-me}"

pass() { echo "PASS  $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL  $1"; FAIL=$((FAIL + 1)); }

echo "=== Sprint 2.1 — Static checks ==="

grep -q '@app.post("/products/{product_id}/quality-check")' app/main.py \
  && pass "route: POST /products/{id}/quality-check exists" \
  || fail "route: quality-check missing"

grep -q "def build_readiness_report" app/main.py \
  && pass "helper: build_readiness_report exists" \
  || fail "helper: build_readiness_report missing"

for file in readiness_report.json readiness_report.md platform_readiness.md missing_assets.md policy_risk_check.md improvement_plan.md; do
  grep -q "$file" app/main.py && pass "report file referenced: $file" || fail "report file missing: $file"
done

grep -q "Run Readiness Check" app/templates/product_edit.html \
  && pass "UI: readiness button exists" \
  || fail "UI: readiness button missing"

grep -q "Package Quality / Upload Readiness" app/templates/product_edit.html \
  && pass "UI: readiness section exists" \
  || fail "UI: readiness section missing"

grep -q "POLICY_HIGH_RISK_KEYWORDS" app/main.py && grep -q "Disney" app/main.py \
  && pass "policy keyword list exists" \
  || fail "policy keyword list missing"

grep -q "readiness_score" app/main.py && grep -q "readiness_status" app/main.py \
  && pass "manifest readiness fields referenced" \
  || fail "manifest readiness fields missing"

python3 -m py_compile app/main.py app/db.py app/llm.py \
  && pass "syntax: app/main.py app/db.py app/llm.py" \
  || fail "syntax check failed"

echo ""
echo "=== Static: PASS=$PASS FAIL=$FAIL ==="

if [ "${LIVE:-0}" != "1" ]; then
  echo "(Set LIVE=1 to run live checks)"
  exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)
fi

echo ""
echo "=== Sprint 2.1 — Live checks ==="

curl -sf "$BASE/health" >/dev/null \
  && pass "live: /health reachable" \
  || fail "live: /health unreachable"

product_id=43
if [ ! -f "products/product_${product_id}.zip" ] || [ ! -f "products/product_${product_id}/manifest.json" ]; then
  curl -si -u "$AUTH_USER:$AUTH_PASS" -X POST "$BASE/products/$product_id/package" --max-redirs 0 >/dev/null 2>&1 || true
fi

resp="$(curl -si -u "$AUTH_USER:$AUTH_PASS" -X POST "$BASE/products/$product_id/package" --max-redirs 0 2>/dev/null || true)"
code="$(echo "$resp" | grep -oP '^HTTP/\S+ \K\d+' | head -1 || echo 0)"
[ "$code" = "303" ] && pass "live: product 43 package route works" || fail "live: product 43 package route failed ($code)"

quality_resp="$(curl -si -u "$AUTH_USER:$AUTH_PASS" -X POST "$BASE/products/$product_id/quality-check" --max-redirs 0 2>/dev/null || true)"
quality_code="$(echo "$quality_resp" | grep -oP '^HTTP/\S+ \K\d+' | head -1 || echo 0)"
quality_location="$(echo "$quality_resp" | grep -i '^location:' | head -1 | tr -d '\r')"
[ "$quality_code" = "303" ] && echo "$quality_location" | grep -q "quality" \
  && pass "live: quality-check redirects with success" \
  || fail "live: quality-check failed (http=$quality_code location=$quality_location)"

quality_dir="products/product_${product_id}/quality"
[ -d "$quality_dir" ] && pass "live: quality folder exists" || fail "live: quality folder missing"

for file in readiness_report.json readiness_report.md platform_readiness.md missing_assets.md policy_risk_check.md improvement_plan.md; do
  [ -f "$quality_dir/$file" ] && pass "live: $file exists" || fail "live: $file missing"
done

python3 - "$quality_dir/readiness_report.json" "products/product_${product_id}/manifest.json" <<'PY'
import json, sys
report = json.load(open(sys.argv[1]))
manifest = json.load(open(sys.argv[2]))
missing = []
if "readiness_score" not in report:
    missing.append("report readiness_score")
if report.get("readiness_status") not in ("ready", "not ready"):
    missing.append("report readiness_status")
if "platform_readiness" not in report:
    missing.append("platform_readiness")
for platform in ["Gumroad", "Fiverr", "Payhip", "Sellfy", "Pinterest"]:
    if platform not in report.get("platform_readiness", {}):
        missing.append(platform)
if "quality_report" not in manifest:
    missing.append("manifest quality_report")
if manifest.get("readiness_score") != report.get("readiness_score"):
    missing.append("manifest readiness_score")
if manifest.get("readiness_status") != report.get("readiness_status"):
    missing.append("manifest readiness_status")
if missing:
    print("missing", missing)
    sys.exit(1)
print(report.get("readiness_score"), report.get("readiness_status"))
PY
[ "$?" -eq 0 ] && pass "live: report and manifest readiness metadata valid" || fail "live: report/manifest readiness metadata invalid"

html="$(curl -sf -u "$AUTH_USER:$AUTH_PASS" "$BASE/products/$product_id/edit" 2>/dev/null || true)"
echo "$html" | grep -q "Package Quality / Upload Readiness" \
  && echo "$html" | grep -q "Overall score" \
  && pass "live: UI renders readiness section and score" \
  || fail "live: UI readiness section/score missing"

python3 - "$quality_dir/readiness_report.json" <<'PY'
import json, sys
report = json.load(open(sys.argv[1]))
print(f"PRODUCT_43_SCORE={report['readiness_score']}")
print(f"PRODUCT_43_STATUS={report['readiness_status']}")
print("PRODUCT_43_BLOCKERS=" + "; ".join(report.get("top_blockers") or []))
PY

echo ""
echo "=== Final: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ] && echo "All Sprint 2.1 checks passed." || echo "$FAIL Sprint 2.1 check(s) failed."
exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)
