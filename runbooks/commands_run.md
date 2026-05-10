# Commands Run

Append-only log of significant shell commands per sprint. Keep tight — not every line, just the meaningful ones.

---

## Sprint 1.2

```bash
# Build / lifecycle
docker compose down
docker compose up -d --build

# Verification
curl http://localhost:8000/health
curl -u admin:change-me -X POST http://localhost:8000/opportunities/mock-scan
curl -u admin:change-me -X POST http://localhost:8000/opportunities/collect/hn
curl -u admin:change-me -X POST http://localhost:8000/opportunities/1/approve
scripts/verify_sprint12.sh
scripts/verify_url_warnings.sh 34

# Compile-only sanity
python3 -m py_compile app/main.py app/db.py app/signal_engine.py app/ruflo_bridge.py
```

## Sprint 1.4

```bash
sed -n '1,320p' runbooks/ROADMAP.md
grep -n "Sprint 1.4" -A120 -B20 runbooks/ROADMAP.md
sed -n '1,260p' runbooks/sprint_1.3_handoff.md
sed -n '1,220p' runbooks/known_issues.md
sed -n '1,220p' runbooks/verification_results.md
python3 -m py_compile app/main.py app/db.py app/llm.py
./scripts/dev_up.sh
./scripts/verify_sprint14.sh
```

## Sprint 1.7

```bash
cd /home/jb/dev/hydra
git status
git log --oneline -10
./scripts/preflight_check.sh
bash scripts/verify_sprint151.sh
LIVE=1 bash scripts/verify_sprint151.sh
./scripts/verify_sprint15.sh
bash scripts/verify_sprint16.sh
ls -la app/alembic/versions
ls -la app/templates
ls -la scripts
ls -la runbooks
find /mnt/c/Users/jbsan/OneDrive/Documents/New\ project\ 2/hydra -maxdepth 3 -type f | sort
python3 -m py_compile app/main.py app/db.py app/llm.py
docker compose run --rm --no-deps hydra-console python -m py_compile /app/main.py /app/db.py /app/llm.py
./scripts/backup_db.sh
docker compose run --rm hydra-console alembic upgrade head
docker compose run --rm hydra-console alembic downgrade 0002
docker compose run --rm hydra-console alembic upgrade head
docker compose run --rm hydra-console alembic current -v
docker compose down
docker compose up -d --build
./scripts/preflight_check.sh
bash scripts/verify_sprint17.sh
LIVE=1 bash scripts/verify_sprint17.sh
bash scripts/verify_sprint16.sh
bash scripts/verify_sprint15.sh
```


## Sprint 1.3

```bash
# Build / lifecycle
docker compose up -d --build
docker compose logs --tail 60 hydra-console

# Read-only inspection
scripts/state_inspect.sh
./scripts/preflight_check.sh
./scripts/status_snapshot.sh

# Verification
scripts/verify_sprint13.sh

# Compile
python3 -m py_compile app/main.py app/db.py app/signal_engine.py app/ruflo_bridge.py
```
