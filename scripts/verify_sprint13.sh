#!/usr/bin/env bash
# Sprint 1.3 — Launch Learning v1 verification.
set +e
AUTH="admin:change-me"
B="http://localhost:8000"
cd /home/jb/dev/hydra

pass() { echo "  PASS — $1"; }
fail() { echo "  FAIL — $1"; FAIL=1; }
header() { echo; echo "=== $1 ==="; }
FAIL=0

header "stack health"
curl -fsS "$B/health" >/dev/null && pass "/health 200" || fail "/health"

header "schema migrations applied"
docker compose exec -T postgres psql -U hydra -d hydra -tA -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='revenue_events'" \
  | grep -q '^source_attribution$' && pass "revenue_events.source_attribution" || fail "revenue_events.source_attribution missing"
docker compose exec -T postgres psql -U hydra -d hydra -tA -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='revenue_events'" \
  | grep -q '^channel_tag$' && pass "revenue_events.channel_tag" || fail "revenue_events.channel_tag missing"
docker compose exec -T postgres psql -U hydra -d hydra -tA -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='product_artifacts'" \
  | grep -q '^published_url$' && pass "product_artifacts.published_url" || fail "product_artifacts.published_url missing"
docker compose exec -T postgres psql -U hydra -d hydra -tA -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='product_artifacts'" \
  | grep -q '^published_at$' && pass "product_artifacts.published_at" || fail "product_artifacts.published_at missing"
docker compose exec -T postgres psql -U hydra -d hydra -tA -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='product_artifacts'" \
  | grep -q '^channel_tag$' && pass "product_artifacts.channel_tag" || fail "product_artifacts.channel_tag missing"
# Unique index intentionally deferred to Sprint 2.0 (Alembic) — see app/db.py.

header "title prefill v2 (no 'Pdf:' prefix)"
# Approve a fresh candidate (id = highest 'new' candidate from HN)
NEW_ID=$(docker compose exec -T postgres psql -U hydra -d hydra -tA -c \
  "SELECT id FROM opportunity_candidates WHERE status='new' AND source='HackerNews' ORDER BY score DESC LIMIT 1")
NEW_ID=$(echo "$NEW_ID" | tr -d '[:space:]')
if [ -z "$NEW_ID" ]; then
  echo "  SKIP — no new HN candidate to approve"
else
  echo "  approving candidate $NEW_ID"
  REDIRECT=$(curl -fsS -u "$AUTH" -X POST -i "$B/opportunities/$NEW_ID/approve" | tr -d '\r' | awk -F': ' '/^location/ {print $2}' | head -1)
  echo "  redirected to $REDIRECT"
  PROD_ID=$(echo "$REDIRECT" | grep -oE '[0-9]+')
  TITLE=$(docker compose exec -T postgres psql -U hydra -d hydra -tA -c "SELECT title FROM products WHERE id = $PROD_ID")
  echo "  title: $TITLE"
  echo "$TITLE" | grep -qiE '^[a-z]+ pdf:' && fail "title still uses '<Format Pdf:' prefix" || pass "title format clean"
fi

header "HN classifier routes coding agents → AI coding tools"
# Insert a synthetic HN candidate via collector reading our own mocked title is impossible without a stub;
# instead, directly test the classifier helper through a Python one-liner inside the container.
docker compose exec -T hydra-console python -c "from main import _hn_classify; v,f = _hn_classify('Show HN: cline-style AI coding agent for Cursor'); print(v); print(f)" 2>&1 | tee /tmp/c.out
grep -q 'AI coding tools' /tmp/c.out && pass "classifier vertical=AI coding tools" || fail "classifier vertical wrong"
grep -q 'cheat sheet PDF' /tmp/c.out && pass "classifier format=cheat sheet PDF" || fail "classifier format wrong"

header "artifact export auto-registers product_files"
# Use product 35 (already has 5 artifacts).
BEFORE=$(docker compose exec -T postgres psql -U hydra -d hydra -tA -c "SELECT count(*) FROM product_files WHERE product_id=35")
RESP=$(curl -fsS -u "$AUTH" -X POST "$B/products/35/artifacts/export")
echo "  export response: $RESP"
AFTER=$(docker compose exec -T postgres psql -U hydra -d hydra -tA -c "SELECT count(*) FROM product_files WHERE product_id=35")
echo "  product_files for product 35: before=$BEFORE after=$AFTER"
# 5 artifacts expected
[ "$AFTER" -eq 5 ] && pass "5 product_files rows registered" || fail "expected 5, got $AFTER"
# Idempotency: second export adds zero
RESP2=$(curl -fsS -u "$AUTH" -X POST "$B/products/35/artifacts/export")
AFTER2=$(docker compose exec -T postgres psql -U hydra -d hydra -tA -c "SELECT count(*) FROM product_files WHERE product_id=35")
[ "$AFTER2" -eq 5 ] && pass "second export is idempotent" || fail "second export added rows ($AFTER2)"

header "distribution publish flow"
# Find the distribution_post artifact for product 35
ART_ID=$(docker compose exec -T postgres psql -U hydra -d hydra -tA -c \
  "SELECT id FROM product_artifacts WHERE product_id=35 AND artifact_type='distribution_post' LIMIT 1")
ART_ID=$(echo "$ART_ID" | tr -d '[:space:]')
if [ -z "$ART_ID" ]; then
  fail "no distribution_post artifact on product 35"
else
  curl -fsS -u "$AUTH" -X POST "$B/products/35/artifacts/$ART_ID/publish" \
    --data-urlencode "published_url=https://x.com/santana802/status/123" \
    --data-urlencode "channel_tag=twitter" -o /dev/null
  PUB=$(docker compose exec -T postgres psql -U hydra -d hydra -tA -c \
    "SELECT channel_tag FROM product_artifacts WHERE id=$ART_ID")
  echo "  channel_tag after publish: $PUB"
  echo "$PUB" | tr -d '[:space:]' | grep -qx 'twitter' && pass "channel_tag stored" || fail "channel_tag not stored"
  # Bad URL
  CODE=$(curl -s -u "$AUTH" -X POST "$B/products/35/artifacts/$ART_ID/publish" \
    --data-urlencode "published_url=not-a-url" -o /dev/null -w '%{http_code}')
  [ "$CODE" = "400" ] && pass "malformed URL rejected with 400" || fail "expected 400 got $CODE"
fi

header "revenue with attribution"
# Create a sale event for product 35 with attribution
curl -fsS -u "$AUTH" -X POST "$B/revenue" \
  --data-urlencode "product_id=35" \
  --data-urlencode "marketplace=gumroad" \
  --data-urlencode "amount=9" \
  --data-urlencode "currency=USD" \
  --data-urlencode "event_type=sale" \
  --data-urlencode "channel_tag=twitter" \
  --data-urlencode "source_attribution=https://x.com/santana802/status/123" \
  --data-urlencode "notes=verification sale" -o /dev/null
ROW=$(docker compose exec -T postgres psql -U hydra -d hydra -tA -c \
  "SELECT channel_tag FROM revenue_events WHERE product_id=35 AND notes='verification sale' ORDER BY id DESC LIMIT 1")
echo "  revenue_event channel_tag: $ROW"
echo "$ROW" | tr -d '[:space:]' | grep -qx 'twitter' && pass "attribution recorded" || fail "attribution missing"

header "launch dashboard renders new sections"
curl -fsS -u "$AUTH" "$B/launch" -o /tmp/launch.html
grep -q 'Revenue by channel' /tmp/launch.html && pass "channel rollup section present" || fail "channel rollup missing"
grep -q 'Live without distribution' /tmp/launch.html && pass "missing-distribution metric present" || fail "missing-distribution missing"

echo
if [ "$FAIL" = "0" ]; then
  echo "VERIFY_SPRINT13 — ALL PASS"
  exit 0
else
  echo "VERIFY_SPRINT13 — FAILURES"
  exit 1
fi
