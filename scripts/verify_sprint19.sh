#!/usr/bin/env bash
# HYDRA Sprint 1.9 verification — Commercial presentation packaging
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

echo "=== Sprint 1.9 — Static checks ==="

grep -q "def _render_cover_preview_html" app/main.py \
  && pass "helper: cover preview HTML generator exists" \
  || fail "helper: cover preview HTML generator missing"

grep -q "def _render_sales_preview_html" app/main.py \
  && pass "helper: sales preview HTML generator exists" \
  || fail "helper: sales preview HTML generator missing"

grep -q "def _write_printable_pdf" app/main.py \
  && pass "helper: simple PDF writer exists" \
  || fail "helper: simple PDF writer missing"

grep -q "fiverr_gig_brief.md" app/main.py \
  && pass "presentation: Fiverr brief generated" \
  || fail "presentation: Fiverr brief missing"

grep -q "mockup_cover_spec.md" app/main.py \
  && pass "presentation: mockup/cover spec generated" \
  || fail "presentation: mockup/cover spec missing"

grep -q "perceived_value_stack.md" app/main.py \
  && pass "presentation: perceived value stack generated" \
  || fail "presentation: perceived value stack missing"

grep -q '"package_version": "1.9"\|"package_version": "2.0"' app/main.py \
  && pass "manifest: package_version 1.9 or newer" \
  || fail "manifest: package_version missing"

grep -q "simple PDF export" app/templates/product_edit.html \
  && pass "UI: package section mentions PDF export" \
  || fail "UI: package section missing PDF copy"

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
echo "=== Sprint 1.9 — Live checks ==="

curl -sf "$BASE/health" >/dev/null \
  && pass "live: /health reachable" \
  || fail "live: /health unreachable"

product_id="$(
docker compose exec -T hydra-console python - <<'PY' | tail -n 1
import json
from decimal import Decimal
from db import Product, ProductArtifact, session_scope

outline = {
    "product_title": "Sprint 1.9 Commerce Planner",
    "tagline": "Make your printable product feel ready to sell.",
    "buyer_persona": "digital product operator",
    "core_pain_solved": "turns generated content into a commercially presentable package",
    "deliverable_sections": [
        {"title": "Daily Sales Focus", "purpose": "Pick the highest-value action", "estimated_length": "1 page"},
        {"title": "Offer Polish Checklist", "purpose": "Review the offer before upload", "estimated_length": "1 page"},
    ],
    "etsy_keyword_angle": "printable sales planner",
    "gumroad_hook": "Package your offer with more confidence before launch.",
    "risk_notes": "none",
}
content = {
    "sections": [
        {"title": "Daily Sales Focus", "content": "Write the product promise, target buyer, primary upload task, and one improvement that raises perceived value."},
        {"title": "Offer Polish Checklist", "content": "Review the cover, preview images, file names, price, description, tags, and customer instructions before publishing."},
    ],
    "total_word_count_estimate": 52,
}
listing = {
    "gumroad": {"title": "Commerce-Ready Printable Planner", "description": "A planner for polishing digital product presentation before launch.", "tags": ["planner", "digital product"]},
    "etsy": {"title": "Printable Sales Planner, Digital Product Launch Checklist", "description": "A clean printable planner for launch preparation.", "tags": ["planner", "printable", "launch"], "category_hint": "Paper & Party Supplies"},
    "sellfy": {"title": "Printable Sales Planner", "description": "A practical launch polish planner."},
    "payhip": {"title": "Printable Sales Planner", "description": "A practical launch polish planner."},
    "universal": {"short_description": "Polish a digital product before upload.", "tagline": "Make the package feel ready to sell."},
}
with session_scope() as session:
    product = Product(
        title="Sprint 1.9 Commerce Planner",
        production_format="planner printable",
        price=Decimal("12"),
        status="draft",
        notes="Created by scripts/verify_sprint19.sh",
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
            source="verify_sprint19",
        ))
    print(product.id)
PY
)"

if [[ "$product_id" =~ ^[0-9]+$ ]]; then
  pass "live: created test product $product_id"
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
  [ -f "$package_dir/preview/cover_preview.html" ] && pass "live: cover preview exists" || fail "live: cover preview missing"
  [ -f "$package_dir/preview/sales_page_preview.html" ] && pass "live: sales preview exists" || fail "live: sales preview missing"
  [ -f "$package_dir/pdf/printable_pack.pdf" ] && pass "live: PDF pack exists" || fail "live: PDF pack missing"
  head -c 5 "$package_dir/pdf/printable_pack.pdf" | grep -q "%PDF-" \
    && pass "live: PDF has PDF header" \
    || fail "live: PDF header invalid"
  [ -f "$package_dir/presentation/gumroad_presentation_assets.md" ] && pass "live: Gumroad assets brief exists" || fail "live: Gumroad assets brief missing"
  [ -f "$package_dir/presentation/fiverr_gig_brief.md" ] && pass "live: Fiverr brief exists" || fail "live: Fiverr brief missing"
  [ -f "$package_dir/presentation/mockup_cover_spec.md" ] && pass "live: mockup/cover spec exists" || fail "live: mockup/cover spec missing"
  [ -f "$package_dir/presentation/perceived_value_stack.md" ] && pass "live: perceived value stack exists" || fail "live: perceived value stack missing"
  python3 - "$package_dir/manifest.json" <<'PY'
import json, sys
manifest = json.load(open(sys.argv[1]))
required = ["pdf_files", "preview_assets", "presentation_assets"]
missing = [key for key in required if not manifest.get(key)]
if manifest.get("package_version") not in ("1.9", "2.0"):
    missing.append("package_version")
if missing:
    print("missing", missing)
    sys.exit(1)
PY
  [ "$?" -eq 0 ] && pass "live: manifest tracks presentation assets" || fail "live: manifest missing presentation metadata"
  python3 - "$zip_path" <<'PY'
import sys, zipfile
zip_path = sys.argv[1]
prefix = zip_path.split("/")[-1].replace(".zip", "")
expected = [
    f"{prefix}/preview/cover_preview.html",
    f"{prefix}/preview/sales_page_preview.html",
    f"{prefix}/pdf/printable_pack.pdf",
    f"{prefix}/presentation/fiverr_gig_brief.md",
    f"{prefix}/presentation/mockup_cover_spec.md",
]
with zipfile.ZipFile(zip_path) as zf:
    names = set(zf.namelist())
missing = [name for name in expected if name not in names]
if missing:
    print("missing", missing)
    sys.exit(1)
PY
  [ "$?" -eq 0 ] && pass "live: ZIP contains commercial assets" || fail "live: ZIP missing commercial assets"
fi

echo ""
echo "=== Final: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ] && echo "All Sprint 1.9 checks passed." || echo "$FAIL Sprint 1.9 check(s) failed."
exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)
