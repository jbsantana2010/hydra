#!/usr/bin/env bash
# HYDRA Sprint 2.0 verification — Visual Commerce Generation Bridge
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

echo "=== Sprint 2.0 — Static checks ==="

grep -q "def _build_visual_theme_intelligence" app/main.py \
  && pass "helper: visual theme intelligence exists" \
  || fail "helper: visual theme intelligence missing"

grep -q "def _build_cover_mockup_prompt_doc" app/main.py \
  && pass "helper: cover/mockup prompt document exists" \
  || fail "helper: cover/mockup prompt document missing"

grep -q "def _build_product_gallery_plan" app/main.py \
  && pass "helper: product gallery plan exists" \
  || fail "helper: product gallery plan missing"

grep -q "def _build_marketplace_visual_specs" app/main.py \
  && pass "helper: marketplace visual specs exists" \
  || fail "helper: marketplace visual specs missing"

grep -q "def _build_image_slot_manifest" app/main.py \
  && pass "helper: image slot manifest exists" \
  || fail "helper: image slot manifest missing"

grep -q "def _build_aesthetic_system_doc" app/main.py \
  && pass "helper: aesthetic system doc exists" \
  || fail "helper: aesthetic system doc missing"

grep -q "def _build_presentation_hierarchy" app/main.py \
  && pass "helper: presentation hierarchy exists" \
  || fail "helper: presentation hierarchy missing"

grep -q '"package_version": "2.0"' app/main.py \
  && pass "manifest: package_version 2.0" \
  || fail "manifest: package_version 2.0 missing"

grep -q "visual_assets" app/main.py \
  && pass "manifest: visual_assets tracked" \
  || fail "manifest: visual_assets missing"

grep -q "Fiverr.*Gumroad.*Pinterest.*Sellfy.*Payhip" app/main.py \
  && pass "platforms: Fiverr/Gumroad/Pinterest/Sellfy/Payhip referenced" \
  || fail "platforms: required visual platforms missing"

grep -q "image generation API called in this sprint" app/main.py \
  && pass "guardrail: image generation explicitly excluded" \
  || fail "guardrail: image generation exclusion missing"

grep -q "visual theme intelligence" app/templates/product_edit.html \
  && pass "UI: package section mentions visual intelligence" \
  || fail "UI: visual intelligence copy missing"

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
echo "=== Sprint 2.0 — Live checks ==="

curl -sf "$BASE/health" >/dev/null \
  && pass "live: /health reachable" \
  || fail "live: /health unreachable"

product_id="$(
docker compose exec -T hydra-console python - <<'PY' | tail -n 1
import json
from decimal import Decimal
from db import Product, ProductArtifact, session_scope

outline = {
    "product_title": "Sprint 2.0 ADHD Focus Planner",
    "tagline": "A calmer way to plan the day.",
    "buyer_persona": "ADHD adults and busy operators",
    "core_pain_solved": "reduces overwhelm by turning the day into visible next actions",
    "deliverable_sections": [
        {"title": "Daily Focus Map", "purpose": "Choose a main task", "estimated_length": "1 page"},
        {"title": "Low-Friction Task List", "purpose": "Break work into next actions", "estimated_length": "1 page"},
    ],
    "etsy_keyword_angle": "ADHD planner printable",
    "gumroad_hook": "Plan the day without adding another app.",
    "risk_notes": "avoid medical claims",
}
content = {
    "sections": [
        {"title": "Daily Focus Map", "content": "Write one main outcome, three supporting actions, and the first tiny step."},
        {"title": "Low-Friction Task List", "content": "Capture each task, mark the next action, and check it off when done."},
    ],
    "total_word_count_estimate": 48,
}
listing = {
    "gumroad": {"title": "ADHD Focus Planner Printable", "description": "A calm printable planner for visible next actions.", "tags": ["adhd", "planner"]},
    "etsy": {"title": "ADHD Planner Printable, Daily Focus Worksheet", "description": "A printable focus planner.", "tags": ["adhd planner", "printable"], "category_hint": "Paper & Party Supplies"},
    "sellfy": {"title": "ADHD Focus Planner", "description": "A calm printable focus planner."},
    "payhip": {"title": "ADHD Focus Planner", "description": "A calm printable focus planner."},
    "universal": {"short_description": "A calm ADHD-friendly planner.", "tagline": "Make the next action visible."},
}
with session_scope() as session:
    product = Product(
        title="Sprint 2.0 ADHD Focus Planner",
        production_format="planner printable",
        price=Decimal("12"),
        status="draft",
        notes="Created by scripts/verify_sprint20.sh",
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
            source="verify_sprint20",
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
  for file in \
    visual/visual_theme_intelligence.json \
    visual/aesthetic_system.md \
    visual/cover_mockup_prompts.md \
    visual/product_gallery_plan.md \
    visual/marketplace_visual_specs.md \
    visual/image_slot_manifest.json \
    visual/presentation_hierarchy.md; do
    [ -f "$package_dir/$file" ] && pass "live: $file exists" || fail "live: $file missing"
  done

  python3 - "$package_dir/manifest.json" "$package_dir/visual/visual_theme_intelligence.json" "$package_dir/visual/image_slot_manifest.json" <<'PY'
import json, sys
manifest = json.load(open(sys.argv[1]))
theme = json.load(open(sys.argv[2]))
slots = json.load(open(sys.argv[3]))
missing = []
if manifest.get("package_version") != "2.0":
    missing.append("manifest package_version")
if not manifest.get("visual_assets"):
    missing.append("visual_assets")
if theme.get("niche") != "adhd_focus":
    missing.append("adhd_focus niche")
for platform in ["Fiverr", "Gumroad", "Pinterest", "Sellfy", "Payhip"]:
    if platform not in theme.get("platforms", []):
        missing.append(platform)
if len(slots.get("slots", [])) < 5:
    missing.append("image slots")
if missing:
    print("missing", missing)
    sys.exit(1)
PY
  [ "$?" -eq 0 ] && pass "live: visual intelligence JSON is valid" || fail "live: visual intelligence JSON invalid"

  grep -q "Pinterest" "$package_dir/visual/marketplace_visual_specs.md" \
    && grep -q "Fiverr" "$package_dir/visual/marketplace_visual_specs.md" \
    && pass "live: marketplace visual specs include target platforms" \
    || fail "live: marketplace visual specs missing target platforms"

  python3 - "$zip_path" <<'PY'
import sys, zipfile
zip_path = sys.argv[1]
prefix = zip_path.split("/")[-1].replace(".zip", "")
expected = [
    f"{prefix}/visual/visual_theme_intelligence.json",
    f"{prefix}/visual/image_slot_manifest.json",
    f"{prefix}/visual/cover_mockup_prompts.md",
    f"{prefix}/visual/product_gallery_plan.md",
    f"{prefix}/visual/marketplace_visual_specs.md",
]
with zipfile.ZipFile(zip_path) as zf:
    names = set(zf.namelist())
missing = [name for name in expected if name not in names]
if missing:
    print("missing", missing)
    sys.exit(1)
PY
  [ "$?" -eq 0 ] && pass "live: ZIP contains visual bridge assets" || fail "live: ZIP missing visual bridge assets"
fi

echo ""
echo "=== Final: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ] && echo "All Sprint 2.0 checks passed." || echo "$FAIL Sprint 2.0 check(s) failed."
exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)
