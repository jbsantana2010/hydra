#!/usr/bin/env bash
# HYDRA Sprint 1.8 verification — Product Asset Generator v1
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

echo "=== Sprint 1.8 — Static checks ==="

grep -q '@app.post("/products/{product_id}/package")' app/main.py \
  && pass "route: POST /products/{id}/package exists" \
  || fail "route: POST /products/{id}/package missing"

grep -q "def build_product_package" app/main.py \
  && pass "helper: build_product_package exists" \
  || fail "helper: build_product_package missing"

grep -q "def _generate_printable_html_files" app/main.py \
  && pass "helper: printable HTML generator exists" \
  || fail "helper: printable HTML generator missing"

grep -q "manifest.json" app/main.py \
  && pass "manifest generation present" \
  || fail "manifest generation missing"

grep -q "Build Product Package" app/templates/product_edit.html \
  && pass "product edit template has package button" \
  || fail "product edit template missing package button"

grep -q "HYDRA_PRODUCT_ROOT" docker-compose.yml \
  && pass "docker compose passes HYDRA_PRODUCT_ROOT" \
  || fail "docker compose missing HYDRA_PRODUCT_ROOT"

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
echo "=== Sprint 1.8 — Live checks ==="

curl -sf "$BASE/health" >/dev/null \
  && pass "live: /health reachable" \
  || fail "live: /health unreachable"

product_id="$(
docker compose exec -T hydra-console python - <<'PY' | tail -n 1
import json
from decimal import Decimal
from db import Product, ProductArtifact, session_scope

outline = {
    "product_title": "Sprint 1.8 Verify Planner",
    "tagline": "A tiny planner for packaging verification.",
    "buyer_persona": "busy solo operator",
    "core_pain_solved": "turns vague tasks into a printable plan",
    "deliverable_sections": [
        {"title": "Daily Overview", "purpose": "Plan the day", "estimated_length": "1 page"},
        {"title": "Task List", "purpose": "Prioritize work", "estimated_length": "1 page"},
    ],
    "etsy_keyword_angle": "printable daily planner",
    "gumroad_hook": "Plan your day without opening another app.",
    "risk_notes": "none",
}
content = {
    "sections": [
        {"title": "Daily Overview", "content": "Write today's focus, appointments, and the one outcome that matters most."},
        {"title": "Task List", "content": "List each task, mark the next action, and check it off when complete."},
    ],
    "total_word_count_estimate": 42,
}
listing = {
    "gumroad": {"title": "Sprint 1.8 Verify Planner", "description": "A printable daily planner.", "tags": ["planner"]},
    "etsy": {"title": "Printable Daily Planner PDF", "description": "A simple printable planner.", "tags": ["planner", "printable"], "category_hint": "Paper & Party Supplies"},
    "sellfy": {"title": "Printable Planner", "description": "Simple printable planner."},
    "payhip": {"title": "Printable Planner", "description": "Simple printable planner."},
    "universal": {"short_description": "A clean printable planner.", "tagline": "Plan the day on paper."},
}
with session_scope() as session:
    product = Product(
        title="Sprint 1.8 Verify Planner",
        production_format="planner printable",
        price=Decimal("9"),
        status="draft",
        notes="Created by scripts/verify_sprint18.sh",
    )
    session.add(product)
    session.flush()
    for artifact_type, payload in (
        ("outline", outline),
        ("product_content", content),
        ("listing_copy", listing),
    ):
        session.add(ProductArtifact(
            product_id=product.id,
            artifact_type=artifact_type,
            title=f"Verify {artifact_type}",
            content=json.dumps(payload),
            source="verify_sprint18",
        ))
    print(product.id)
PY
)"

if [[ "$product_id" =~ ^[0-9]+$ ]]; then
  pass "live: created test product $product_id with required artifacts"
else
  fail "live: failed to create test product (got '$product_id')"
fi

if [[ "$product_id" =~ ^[0-9]+$ ]]; then
  resp="$(curl -si -u "$AUTH_USER:$AUTH_PASS" -X POST "$BASE/products/$product_id/package" --max-redirs 0 2>/dev/null || true)"
  code="$(echo "$resp" | grep -oP '^HTTP/\S+ \K\d+' | head -1 || echo 0)"
  location="$(echo "$resp" | grep -i '^location:' | head -1 | tr -d '\r')"
  [ "$code" = "303" ] && echo "$location" | grep -q "flash=success" \
    && pass "live: package route redirects with success" \
    || fail "live: package route failed (http=$code location=$location)"

  package_dir="products/product_$product_id"
  zip_path="products/product_$product_id.zip"
  [ -f "$zip_path" ] && pass "live: ZIP exists" || fail "live: ZIP missing at $zip_path"
  [ -f "$package_dir/README.md" ] && pass "live: README exists" || fail "live: README missing"
  [ -f "$package_dir/manifest.json" ] && pass "live: manifest exists" || fail "live: manifest missing"
  [ -f "$package_dir/source/outline.md" ] && [ -f "$package_dir/source/product_content.md" ] && [ -f "$package_dir/source/listing_copy.md" ] \
    && pass "live: source markdown files exist" \
    || fail "live: source markdown missing"
  find "$package_dir/printable" -type f -name '*.html' | grep -q . \
    && pass "live: printable HTML exists" \
    || fail "live: printable HTML missing"

  python3 - "$zip_path" <<'PY'
import sys, zipfile
zip_path = sys.argv[1]
with zipfile.ZipFile(zip_path) as zf:
    names = set(zf.namelist())
required = {"README.md", "manifest.json", "marketplace_checklist.md"}
prefix = zip_path.split("/")[-1].replace(".zip", "")
missing = [name for name in required if f"{prefix}/{name}" not in names]
if missing:
    print("missing", missing)
    sys.exit(1)
PY
  [ "$?" -eq 0 ] && pass "live: ZIP contains package metadata" || fail "live: ZIP missing metadata"

  row_count="$(docker compose exec -T postgres psql -U hydra -d hydra -tAc "select count(*) from product_files where product_id=$product_id and file_type='package_zip';" 2>/dev/null | tr -d '[:space:]')"
  [ "${row_count:-0}" -ge 1 ] \
    && pass "live: product_files row registered" \
    || fail "live: product_files package row missing"
fi

echo ""
echo "=== Final: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ] && echo "All Sprint 1.8 checks passed." || echo "$FAIL Sprint 1.8 check(s) failed."
exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)
