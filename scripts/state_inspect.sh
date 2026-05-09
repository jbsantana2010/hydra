#!/usr/bin/env bash
# One-shot read-only inspection for resume/recovery.
set +e
cd /home/jb/dev/hydra

echo "=== preflight ==="
./scripts/preflight_check.sh 2>&1 | tail -25

echo
echo "=== status snapshot ==="
./scripts/status_snapshot.sh 2>&1 | tail -25

echo
echo "=== docker compose ps ==="
docker compose ps

echo
echo "=== /health ==="
curl -s http://localhost:8000/health
echo

echo
echo "=== product 35 row ==="
docker compose exec -T postgres psql -U hydra -d hydra -c "SELECT id, opportunity_id, title, production_format, price, status, gumroad_url FROM products WHERE id = 35;"

echo
echo "=== latest products ==="
docker compose exec -T postgres psql -U hydra -d hydra -c "SELECT id, title, status, price, COALESCE(gumroad_url,'') AS url FROM products ORDER BY id DESC LIMIT 8;"

echo
echo "=== revenue rows ==="
docker compose exec -T postgres psql -U hydra -d hydra -c "SELECT id, product_id, marketplace, amount, currency, event_type, created_at FROM revenue_events ORDER BY id DESC LIMIT 10;"

echo
echo "=== artifacts for product 35 ==="
docker compose exec -T postgres psql -U hydra -d hydra -c "SELECT id, artifact_type, COALESCE(title,'') AS title, source, created_at FROM product_artifacts WHERE product_id = 35 ORDER BY id;"

echo
echo "=== product files for product 35 ==="
docker compose exec -T postgres psql -U hydra -d hydra -c "SELECT id, file_label, file_path, file_type, created_at FROM product_files WHERE product_id = 35 ORDER BY id;"

echo
echo "=== approved opportunity count ==="
docker compose exec -T postgres psql -U hydra -d hydra -c "SELECT status, COUNT(*) FROM opportunity_candidates GROUP BY status ORDER BY status;"

echo
echo "=== untracked dirs in repo root ==="
ls -la /home/jb/dev/hydra/products /home/jb/dev/hydra/ruflo 2>&1 | head -30

echo
echo "STATE_INSPECT_DONE"
