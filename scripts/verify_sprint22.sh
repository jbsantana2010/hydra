#!/usr/bin/env bash
# verify_sprint22.sh — Sprint 2.2 verification
# Usage:
#   bash scripts/verify_sprint22.sh          # static checks only
#   LIVE=1 bash scripts/verify_sprint22.sh   # static + live checks (stack must be running)
#   BUILD=1 bash scripts/verify_sprint22.sh  # also runs the kit builder (needs ANTHROPIC_API_KEY or uses fallback)

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PASS=0; FAIL=0; WARN=0
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'; BOLD='\033[1m'

pass() { echo -e "  ${GREEN}✓${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}✗${NC} $1"; FAIL=$((FAIL + 1)); }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; WARN=$((WARN + 1)); }
header() { echo -e "\n${BOLD}$1${NC}"; }

# ── Helpers ────────────────────────────────────────────────────────────────
file_exists()    { [ -f "$1" ] && pass "File exists: $1" || fail "Missing: $1"; }
dir_exists()     { [ -d "$1" ] && pass "Dir exists: $1"  || fail "Missing dir: $1"; }
file_contains()  { grep -q -- "$2" "$1" 2>/dev/null && pass "$3" || fail "$3"; }
file_gt_lines()  { local n; n=$(wc -l < "$1" 2>/dev/null || echo 0); [ "$n" -ge "$2" ] && pass "$3 ($n lines)" || fail "$3 (only $n lines)"; }

# ── STATIC CHECKS ──────────────────────────────────────────────────────────
header "[ Sprint 2.2 Static Checks ]"

header "1. Core Sprint 2.2 files"
file_exists "app/kit_generator.py"
file_exists "app/kit_covers.py"
file_exists "app/kit_routes.py"
file_exists "app/templates/kit_document.html"
file_exists "app/templates/kit_status.html"
file_exists "scripts/build_product43_kit.py"

header "2. kit_document.html — professional template"
file_gt_lines "app/templates/kit_document.html" 200 "kit_document.html is substantial (≥200 lines)"
file_contains "app/templates/kit_document.html" "cover-page" "Has cover page section"
file_contains "app/templates/kit_document.html" "workflow-step" "Has workflow step component"
file_contains "app/templates/kit_document.html" "prompt-card" "Has prompt block component"
file_contains "app/templates/kit_document.html" "callout" "Has callout component"
file_contains "app/templates/kit_document.html" "checklist" "Has checklist component"
file_contains "app/templates/kit_document.html" "data-table" "Has table component"
file_contains "app/templates/kit_document.html" "quick-win-box" "Has quick win box component"
file_contains "app/templates/kit_document.html" "roadmap-phase" "Has implementation roadmap component"
file_contains "app/templates/kit_document.html" "--navy" "Uses navy color system"
file_contains "app/templates/kit_document.html" "--gold" "Uses gold accent system"
file_contains "app/templates/kit_document.html" "@page" "Has print/PDF @page rules"
file_contains "app/templates/kit_document.html" "page-break" "Has page break support"
file_contains "app/templates/kit_document.html" "doc-header-strip" "Has document header strip"
file_contains "app/templates/kit_document.html" "purpose-block" "Has purpose block"
file_contains "app/templates/kit_document.html" "toc-block" "Has table of contents"

header "3. kit_covers.py — SVG generator"
file_gt_lines "app/kit_covers.py" 80 "kit_covers.py is substantial"
file_contains "app/kit_covers.py" "generate_document_cover_svg" "Has document cover function"
file_contains "app/kit_covers.py" "generate_master_cover_svg" "Has master cover function"
file_contains "app/kit_covers.py" "build_kit_covers" "Has kit cover builder"
file_contains "app/kit_covers.py" "cover_MASTER.svg" "Generates master cover"
file_contains "app/kit_covers.py" "#1a2744" "Uses navy color"
file_contains "app/kit_covers.py" "#c9a84c" "Uses gold accent"

header "4. kit_generator.py — content generation"
file_gt_lines "app/kit_generator.py" 150 "kit_generator.py is substantial"
file_contains "app/kit_generator.py" "SYSTEM_PROMPT" "Has professional system prompt"
file_contains "app/kit_generator.py" "quick_start" "Has Quick Start prompt"
file_contains "app/kit_generator.py" "listing_descriptions" "Has Listing Description prompt"
file_contains "app/kit_generator.py" "lead_followup" "Has Lead Follow-Up prompt"
file_contains "app/kit_generator.py" "client_onboarding" "Has Client Onboarding prompt"
file_contains "app/kit_generator.py" "social_media" "Has Social Media prompt"
file_contains "app/kit_generator.py" "negotiation" "Has Negotiation prompt"
file_contains "app/kit_generator.py" "reputation" "Has Reputation prompt"
file_contains "app/kit_generator.py" "html_to_pdf" "Has PDF renderer"
file_contains "app/kit_generator.py" "assemble_master_pdf" "Has master PDF assembler"
file_contains "app/kit_generator.py" "build_zip" "Has ZIP packager"
file_contains "app/kit_generator.py" "weasyprint" "Tries WeasyPrint first"
file_contains "app/kit_generator.py" "pdfkit" "Falls back to pdfkit"

header "5. kit_routes.py — FastAPI router"
file_contains "app/kit_routes.py" "kit_router" "Exports kit_router"
file_contains "app/kit_routes.py" "APIRouter" "Uses FastAPI APIRouter"
file_contains "app/kit_routes.py" "generate_kit_route" "Has generate route"
file_contains "app/kit_routes.py" "generate_covers_only" "Has covers-only route"
file_contains "app/kit_routes.py" "download_kit_file" "Has download route"
file_contains "app/kit_routes.py" "delete_kit" "Has delete route"
file_contains "app/main.py" "from kit_routes import kit_router" "Router imported in main.py"
file_contains "app/main.py" "app.include_router(kit_router)" "Router included in FastAPI app"

header "6. build_product43_kit.py — standalone builder"
file_contains "scripts/build_product43_kit.py" "PRODUCT_ID  = 43" "Targets product 43"
file_contains "scripts/build_product43_kit.py" "Real Estate AI Mastery Kit" "Has kit name"
file_contains "scripts/build_product43_kit.py" "HYDRA kit LLM adapter not enabled" \
  "Uses deterministic fallback without direct provider calls"
file_contains "scripts/build_product43_kit.py" "covers-only" "Has covers-only flag"
file_contains "scripts/build_product43_kit.py" "no-pdf" "Has no-pdf flag"
file_contains "scripts/build_product43_kit.py" "build_kit_covers" "Calls cover builder"

header "7. Python syntax check"
for f in app/kit_generator.py app/kit_covers.py app/kit_routes.py scripts/build_product43_kit.py; do
  python3 -c "
import ast, sys
with open('$f') as fh:
    src = fh.read()
try:
    ast.parse(src)
    print('  ok')
except SyntaxError as e:
    print(f'  SYNTAX ERROR: {e}')
    sys.exit(1)
" && pass "Syntax OK: $f" || fail "Syntax error: $f"
done

header "8. Jinja2 template parseable"
python3 - <<'PYEOF'
import sys
try:
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("app/templates"))
    tpl = env.get_template("kit_document.html")
    print("  ok")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)
PYEOF
[ $? -eq 0 ] && pass "kit_document.html parses as valid Jinja2" || fail "kit_document.html Jinja2 parse error"

# ── BUILD CHECK (optional) ─────────────────────────────────────────────────
if [ "${BUILD:-0}" = "1" ]; then
  header "[ Build Check — Covers Only (no LLM required) ]"
  BUILD_ROOT="${HYDRA_SPRINT22_BUILD_ROOT:-/tmp/hydra_sprint22_build}"
  rm -rf "$BUILD_ROOT"
  echo "  Running: python3 scripts/build_product43_kit.py --covers-only --out $BUILD_ROOT"
  python3 scripts/build_product43_kit.py --covers-only --out "$BUILD_ROOT" 2>&1 | tail -20

  COVERS_DIR="$BUILD_ROOT/product_43/covers"
  if [ -d "$COVERS_DIR" ]; then
    SVG_COUNT=$(find "$COVERS_DIR" -name "*.svg" | wc -l)
    if [ "$SVG_COUNT" -ge 9 ]; then
      pass "Generated $SVG_COUNT SVG covers in $COVERS_DIR"
    else
      warn "Only $SVG_COUNT SVG covers found (expected 9)"
    fi
    file_exists "$COVERS_DIR/cover_MASTER.svg"
    file_exists "$COVERS_DIR/cover_00.svg"
    file_exists "$COVERS_DIR/cover_07.svg"
  else
    fail "covers/ directory not created"
  fi
fi

# ── LIVE CHECKS (optional) ─────────────────────────────────────────────────
if [ "${LIVE:-0}" = "1" ]; then
  BASE="${HYDRA_BASE_URL:-http://localhost:8000}"
  AUTH_USER="${HYDRA_BASIC_USER:-admin}"
  AUTH_PASS="${HYDRA_BASIC_PASS:-change-me}"
  header "[ Live Checks — $BASE ]"

  # Kit status page (product 43)
  code=$(curl -s -u "$AUTH_USER:$AUTH_PASS" -o /dev/null -w "%{http_code}" "$BASE/kits/43" 2>/dev/null || echo "0")
  [ "$code" = "200" ] && pass "GET /kits/43 → 200" || fail "GET /kits/43 → $code (router not wired?)"

  # Check covers endpoint (fast, no LLM)
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -u "$AUTH_USER:$AUTH_PASS" \
    -X POST "$BASE/kits/43/covers?kit_name=Real+Estate+AI+Mastery+Kit&kit_tagline=Test" \
    --max-redirs 0 2>/dev/null || echo "0")
  [ "$code" = "303" ] && pass "POST /kits/43/covers → 303 redirect" || \
    warn "POST /kits/43/covers → $code (expected 303)"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Sprint 2.2 Verification: ${GREEN}$PASS passed${NC}  ${RED}$FAIL failed${NC}  ${YELLOW}$WARN warnings${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ "$FAIL" -eq 0 ]; then
  echo ""
  echo -e "  ${GREEN}Sprint 2.2 static checks passed.${NC}"
  echo ""
  echo "  Sprint 2.2 is wired into the FastAPI app. Use LIVE=1 for route checks"
  echo "  and BUILD=1 for a deterministic covers-only build check."
  echo ""
  exit 0
else
  echo ""
  echo -e "  ${RED}$FAIL check(s) failed. See above.${NC}"
  echo ""
  exit 1
fi
