#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PRODUCT_ID="${PRODUCT_ID:-43}"
PRODUCT_DIR="products/product_${PRODUCT_ID}"
FINAL_DIR="$PRODUCT_DIR/final_assets"
failures=0

pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1"; failures=$((failures + 1)); }
check_file() { [[ -s "$1" ]] && pass "$2" || fail "$2"; }
check_dir() { [[ -d "$1" ]] && pass "$2" || fail "$2"; }
check_grep() { grep -q "$1" "$2" && pass "$3" || fail "$3"; }

echo "HYDRA Sprint 2.9 — Marketplace Export Verification"

python3 -m py_compile app/marketplace_export.py app/kit_covers.py app/aesthetica.py \
  && pass "export modules compile" || fail "export modules compile"

PYTHONPATH=app python3 -m marketplace_export >/tmp/hydra_sprint29_export.out \
  && pass "marketplace export pipeline runs" || {
    cat /tmp/hydra_sprint29_export.out || true
    fail "marketplace export pipeline runs"
  }

check_dir "$FINAL_DIR/gumroad" "gumroad final folder exists"
check_dir "$FINAL_DIR/fiverr" "fiverr final folder exists"
check_dir "$FINAL_DIR/archive" "source SVG archive folder exists"
check_dir "$PRODUCT_DIR/archive" "obsolete archive folder exists"
check_file "$FINAL_DIR/ASSET_MANIFEST.md" "asset manifest exists"

for file in \
  gumroad/thumbnail_square.png \
  gumroad/hero_cover.png \
  gumroad/value_stack.png \
  gumroad/included_documents.png \
  gumroad/product_mockup.png \
  fiverr/fiverr_main_1280x769.png \
  fiverr/fiverr_secondary.png; do
  check_file "$FINAL_DIR/$file" "$file exists and is non-empty"
done

PYTHONPATH=app python3 - <<PY
from pathlib import Path
from PIL import Image

expected = {
    "gumroad/thumbnail_square.png": (1200, 1200),
    "gumroad/hero_cover.png": (1600, 900),
    "gumroad/value_stack.png": (1280, 769),
    "gumroad/included_documents.png": (1280, 769),
    "gumroad/product_mockup.png": (1280, 769),
    "fiverr/fiverr_main_1280x769.png": (1280, 769),
    "fiverr/fiverr_secondary.png": (1280, 720),
}
base = Path("$FINAL_DIR")
for rel, dims in expected.items():
    path = base / rel
    with Image.open(path) as img:
        assert img.size == dims, f"{rel}: {img.size} != {dims}"
        assert img.format == "PNG", f"{rel}: {img.format}"
print("dimensions ok", len(expected))
PY
pass "PNG dimensions and formats are correct"

if find "$FINAL_DIR/archive" -type f ! -name '*.svg' | grep -q .; then
  fail "final source archive contains SVGs only"
else
  pass "final source archive contains SVGs only"
fi

if [[ -d "$PRODUCT_DIR/marketplace_visuals/variants" ]]; then
  fail "obsolete palette variants removed from active marketplace visuals"
else
  pass "obsolete palette variants removed from active marketplace visuals"
fi

check_dir "$PRODUCT_DIR/archive/marketplace_visuals_obsolete/variants" "obsolete variants archived"
check_grep "thumbnail_square.png" "$FINAL_DIR/ASSET_MANIFEST.md" "manifest names Gumroad square thumbnail"
check_grep "No screenshots are required" "$FINAL_DIR/ASSET_MANIFEST.md" "manifest says screenshots are not required"

bash scripts/verify_sprint282.sh >/tmp/hydra_sprint282_regression.out \
  && pass "Sprint 2.8.2 regression passes" || {
    cat /tmp/hydra_sprint282_regression.out || true
    fail "Sprint 2.8.2 regression passes"
  }

if [[ "$failures" -eq 0 ]]; then
  echo "SPRINT 2.9 VERIFY: PASS"
else
  echo "SPRINT 2.9 VERIFY: FAIL ($failures)"
  exit 1
fi
