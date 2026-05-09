#!/usr/bin/env bash
# Sprint 1.2 verification (one-shot, idempotent enough for repeated runs).
set -euo pipefail
AUTH="admin:change-me"
BASE="http://localhost:8000"

echo "--- /health ---"
curl -fsS "$BASE/health"; echo

echo "--- mock SIGNAL scan (idempotent) ---"
curl -fsS -u "$AUTH" -X POST "$BASE/opportunities/mock-scan"; echo

echo "--- approve candidate id=1 (auto-prefill) ---"
curl -fsS -u "$AUTH" -X POST -i "$BASE/opportunities/1/approve" | head -5

LATEST_ID=$(curl -fsS -u "$AUTH" "$BASE/launch" | grep -oE '/products/[0-9]+/edit' | head -1 | grep -oE '[0-9]+')
echo "latest product id from /launch: $LATEST_ID"

echo "--- product edit page snippets ---"
curl -fsS -u "$AUTH" "$BASE/products/$LATEST_ID/edit" -o /tmp/p_edit.html
echo "title input:"
grep -oE 'name="title"[^>]*value="[^"]+' /tmp/p_edit.html | head -1
echo "format input:"
grep -oE 'name="production_format"[^>]*value="[^"]+' /tmp/p_edit.html | head -1
echo "price input:"
grep -oE 'name="price"[^>]*value="[^"]+' /tmp/p_edit.html | head -1
echo "notes (first 8 lines):"
sed -n '/name="notes"/,/<\/textarea>/p' /tmp/p_edit.html | sed 's/<[^>]*>//g' | sed '/^$/d' | head -8

echo "--- add a file record ---"
curl -fsS -u "$AUTH" -X POST -i "$BASE/products/$LATEST_ID/files" \
  --data-urlencode "file_label=main_zip" \
  --data-urlencode "file_path=products/test/test.zip" \
  --data-urlencode "file_type=zip" \
  --data-urlencode "notes=verification run" | head -3

echo "--- add an artifact ---"
curl -fsS -u "$AUTH" -X POST -i "$BASE/products/$LATEST_ID/artifacts" \
  --data-urlencode "artifact_type=outline" \
  --data-urlencode "title=Verification outline" \
  --data-urlencode "content=## Promise\nVerification\n## Sections\n- A\n- B" \
  --data-urlencode "source=ruflo" | head -3

echo "--- export artifacts ---"
curl -fsS -u "$AUTH" -X POST "$BASE/products/$LATEST_ID/artifacts/export"; echo

echo "--- enable kill switch and retry HN collect ---"
curl -fsS -u "$AUTH" -X POST -d "enabled=true" "$BASE/settings/kill-switch" -i | head -3
HN_BLOCKED=$(curl -s -u "$AUTH" -X POST -d "query=AI" "$BASE/opportunities/collect/hn" -w '\nHTTP=%{http_code}\n')
echo "$HN_BLOCKED"

echo "--- disable kill switch ---"
curl -fsS -u "$AUTH" -X POST -d "enabled=false" "$BASE/settings/kill-switch" -i | head -3

echo "--- gumroad URL warnings ---"
echo "set status=live, no URL:"
curl -fsS -u "$AUTH" -X POST "$BASE/products/$LATEST_ID/edit" \
  --data-urlencode "title=Verification Product" \
  --data-urlencode "production_format=cheat sheet PDF" \
  --data-urlencode "price=9" \
  --data-urlencode "status=live" \
  --data-urlencode "gumroad_url=" \
  --data-urlencode "notes=verification" -i | head -3
curl -fsS -u "$AUTH" "$BASE/products/$LATEST_ID/edit" | grep -oE 'banner (warn|good)[^<]*<[^>]*>[^<]+' | head -1
echo "now set malformed URL:"
curl -fsS -u "$AUTH" -X POST "$BASE/products/$LATEST_ID/edit" \
  --data-urlencode "title=Verification Product" \
  --data-urlencode "production_format=cheat sheet PDF" \
  --data-urlencode "price=9" \
  --data-urlencode "status=live" \
  --data-urlencode "gumroad_url=gumroad.com/l/x" \
  --data-urlencode "notes=verification" -i | head -3
curl -fsS -u "$AUTH" "$BASE/products/$LATEST_ID/edit" | grep -oE 'banner (warn|good)[^<]*<[^>]*>[^<]+' | head -1
echo "now set proper URL:"
curl -fsS -u "$AUTH" -X POST "$BASE/products/$LATEST_ID/edit" \
  --data-urlencode "title=Verification Product" \
  --data-urlencode "production_format=cheat sheet PDF" \
  --data-urlencode "price=9" \
  --data-urlencode "status=live" \
  --data-urlencode "gumroad_url=https://example.gumroad.com/l/test" \
  --data-urlencode "notes=verification" -i | head -3
curl -fsS -u "$AUTH" "$BASE/products/$LATEST_ID/edit" | grep -oE 'banner (warn|good)[^<]*<[^>]*>[^<]+' | head -1

echo
echo "--- exports on host ---"
ls -la /home/jb/dev/hydra/exports/product_$LATEST_ID/ 2>&1 | head -10

echo
echo "VERIFICATION_DONE"
