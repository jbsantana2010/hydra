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
