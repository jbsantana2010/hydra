#!/usr/bin/env bash
set -euo pipefail
AUTH="admin:change-me"
B="http://localhost:8000"
PID="${1:-34}"

post_edit() {
  local url="$1"
  curl -fsS -u "$AUTH" -X POST "$B/products/$PID/edit" \
    --data-urlencode "title=URLTest" \
    --data-urlencode "production_format=PDF" \
    --data-urlencode "price=9" \
    --data-urlencode "status=live" \
    --data-urlencode "gumroad_url=$url" \
    --data-urlencode "notes=x" >/dev/null
}

extract_banner() {
  curl -fsS -u "$AUTH" "$B/products/$PID/edit" \
    | python3 -c "import sys,re; m=re.search(r'<div class=\"banner ([^\"]+)\">\s*([^<]+)', sys.stdin.read()); print('NO BANNER' if not m else f'{m.group(1).strip()} :: {m.group(2).strip()}')"
}

echo "case 1 — live + empty URL:"
post_edit ""
extract_banner

echo
echo "case 2 — malformed URL:"
post_edit "gumroad.com/x"
extract_banner

echo
echo "case 3 — proper https URL:"
post_edit "https://example.gumroad.com/l/x"
extract_banner

echo
echo "case 4 — files section on page:"
curl -fsS -u "$AUTH" "$B/products/$PID/edit" | grep -oE 'main_zip|products/test/test\.zip' | sort -u
