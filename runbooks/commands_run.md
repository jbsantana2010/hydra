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

## Sprint 1.8

```bash
cd /home/jb/dev/hydra
git status
git log --oneline -10
./scripts/preflight_check.sh
bash scripts/verify_sprint17.sh
LIVE=1 bash scripts/verify_sprint17.sh
ls app/templates
ls scripts
ls runbooks
sed -n '1,260p' app/main.py
sed -n '1,260p' app/db.py
sed -n '1,260p' runbooks/sprint_1.7_handoff.md
python3 -m py_compile app/main.py app/db.py app/llm.py
chmod +x scripts/verify_sprint18.sh
bash scripts/verify_sprint18.sh
docker compose up -d --build
./scripts/preflight_check.sh
LIVE=1 bash scripts/verify_sprint18.sh
curl -si -u admin:change-me -X POST http://localhost:8000/products/43/package --max-redirs 0
find products/product_43 -maxdepth 3 -type f | sort
```

## Sprint 1.9

```bash
cd /home/jb/dev/hydra
git status --short
git log --oneline -5
./scripts/preflight_check.sh
bash scripts/verify_sprint18.sh
sed -n '1200,1520p' app/main.py
sed -n '1,240p' app/templates/product_edit.html
python3 -m py_compile app/main.py app/db.py app/llm.py
chmod +x scripts/verify_sprint19.sh
bash scripts/verify_sprint19.sh
docker compose up -d --build
./scripts/preflight_check.sh
LIVE=1 bash scripts/verify_sprint19.sh
curl -si -u admin:change-me -X POST http://localhost:8000/products/43/package --max-redirs 0
find products/product_43 -maxdepth 3 -type f | sort
python3 -m json.tool products/product_43/manifest.json
head -c 5 products/product_43/pdf/printable_pack.pdf | od -An -tx1
bash scripts/verify_sprint18.sh
LIVE=1 bash scripts/verify_sprint18.sh
```

## Sprint 2.0

```bash
cd /home/jb/dev/hydra
git status --short
git log --oneline -6
./scripts/preflight_check.sh
bash scripts/verify_sprint19.sh
python3 -m py_compile app/main.py app/db.py app/llm.py
chmod +x scripts/verify_sprint20.sh
bash scripts/verify_sprint20.sh
docker compose up -d --build
./scripts/preflight_check.sh
LIVE=1 bash scripts/verify_sprint20.sh
bash scripts/verify_sprint19.sh
LIVE=1 bash scripts/verify_sprint19.sh
curl -si -u admin:change-me -X POST http://localhost:8000/products/43/package --max-redirs 0
find products/product_43/visual -maxdepth 2 -type f | sort
python3 -m json.tool products/product_43/manifest.json
python3 -m json.tool products/product_43/visual/visual_theme_intelligence.json
```

## Sprint 2.1

```bash
cd /home/jb/dev/hydra
git status --short
git log --oneline -6
./scripts/preflight_check.sh
bash scripts/verify_sprint20.sh
python3 -m py_compile app/main.py app/db.py app/llm.py
chmod +x scripts/verify_sprint21.sh
bash scripts/verify_sprint21.sh
docker compose up -d --build
./scripts/preflight_check.sh
LIVE=1 bash scripts/verify_sprint21.sh
bash scripts/verify_sprint20.sh
LIVE=1 bash scripts/verify_sprint20.sh
find products/product_43/quality -maxdepth 1 -type f | sort
python3 -m json.tool products/product_43/quality/readiness_report.json
```

## Sprint 2.2

```bash
cd /home/jb/dev/hydra
git status
git log --oneline -10
ls app
ls app/templates
ls scripts
python3 -m py_compile app/main.py app/db.py app/llm.py app/kit_covers.py app/kit_generator.py app/kit_routes.py
bash scripts/verify_sprint22.sh
BUILD=1 bash scripts/verify_sprint22.sh
python3 -m venv /tmp/hydra_sprint22_venv
/tmp/hydra_sprint22_venv/bin/pip install -r app/requirements.txt
PYTHONPATH=app /tmp/hydra_sprint22_venv/bin/python - <<'PY'
import main
routes = sorted(getattr(route, "path", "") for route in main.app.routes)
print([path for path in routes if path.startswith("/kits/")])
PY
/tmp/hydra_sprint22_venv/bin/python scripts/build_product43_kit.py --out /tmp/hydra_sprint22_full_build
find /tmp/hydra_sprint22_full_build/product_43 -maxdepth 2 -type f | sort
./scripts/preflight_check.sh || true
LIVE=1 bash scripts/verify_sprint22.sh || true
```

## Sprint 2.3

```bash
cd /home/jb/dev/hydra
bash scripts/verify_sprint23.sh
LIVE=1 bash scripts/verify_sprint22.sh
bash scripts/verify_sprint23_llm_persistence.sh
docker compose up -d --build hydra-console
curl -s -i -u admin:change-me -X POST http://localhost:8000/kits/43/generate \
  -d 'kit_name=Real Estate AI Mastery Kit' \
  -d 'kit_tagline=The complete AI implementation system for modern agents' \
  -d 'niche=Real Estate Agents' \
  -d 'niche_context=Professional real estate agents seeking AI implementation guidance' \
  -d 'kit_edition=2026 Edition' \
  -d 'theme=real_estate'
bash scripts/verify_sprint23.sh
LIVE=1 bash scripts/verify_sprint22.sh
bash scripts/verify_sprint23_llm_persistence.sh
grep -R -F 'CONTENT PENDING' products/product_43 || true
grep -R -F 'LLM generation was not available' products/product_43 || true
ls products/product_43/*.html | wc -l
ls products/product_43/pdf/*.pdf | wc -l
ls -lah products/product_43/*.zip
docker compose exec -T postgres psql -U hydra -d hydra -Atc 'select purpose, count(1) from llm_calls group by purpose order by purpose;'
python3 -m json.tool products/product_43/kit_generation_report.json
```

## Sprint 2.4

```bash
cd /home/jb/dev/hydra
python3 -m py_compile app/kit_covers.py app/kit_generator.py app/kit_routes.py
docker compose up -d --build hydra-console
curl -s -i -u admin:change-me -X POST http://localhost:8000/kits/43/generate \
  -d 'kit_name=Real Estate AI Mastery Kit' \
  -d 'kit_tagline=The complete AI implementation system for modern agents' \
  -d 'niche=Real Estate Agents' \
  -d 'niche_context=Professional real estate agents seeking AI implementation guidance' \
  -d 'kit_edition=2026 Edition' \
  -d 'theme=real_estate'
chmod +x scripts/verify_sprint24.sh
bash scripts/verify_sprint24.sh
LIVE=1 bash scripts/verify_sprint24.sh
bash scripts/verify_sprint23.sh
find products/product_43/marketplace_visuals -maxdepth 1 -type f -printf '%f %s bytes\n' | sort
ls -lh products/product_43/covers/cover_MASTER.svg \
  products/product_43/marketplace_visuals/fiverr_gig_image_1280x769.svg \
  products/product_43/02_Listing_Description_System.pdf \
  products/product_43/MASTER_Complete_Kit.pdf
```

## Sprint 2.5

```bash
cd /home/jb/dev/hydra
python3 -m py_compile app/kit_covers.py
docker compose up -d --build hydra-console
curl -s -i -u admin:change-me -X POST http://localhost:8000/kits/43/generate \
  -d 'kit_name=Real Estate AI Mastery Kit' \
  -d 'kit_tagline=The complete AI implementation system for modern agents' \
  -d 'niche=Real Estate Agents' \
  -d 'niche_context=Professional real estate agents seeking AI implementation guidance' \
  -d 'kit_edition=2026 Edition' \
  -d 'theme=navy_gold'
chmod +x scripts/verify_sprint25.sh
bash scripts/verify_sprint25.sh
LIVE=1 bash scripts/verify_sprint25.sh
bash scripts/verify_sprint24.sh
bash scripts/verify_sprint23.sh
find products/product_43/marketplace_visuals/variants -maxdepth 2 -type f | sort
ls -lh products/product_43/marketplace_visuals/variants/index.html \
  products/product_43/marketplace_visuals/variants/export_notes.md
```

## Sprint 2.6

```bash
cd /home/jb/dev/hydra
python3 -m py_compile app/aesthetica.py app/main.py
chmod +x scripts/verify_sprint26.sh
bash scripts/verify_sprint26.sh
docker compose up -d --build hydra-console
LIVE=1 bash scripts/verify_sprint26.sh
bash scripts/verify_sprint25.sh
```

## Sprint 2.8.1

```bash
cd /home/jb/dev/hydra
python3 -m py_compile app/kit_covers.py app/aesthetica.py
python3 scripts/build_product43_kit.py --covers-only
chmod +x scripts/verify_sprint281.sh
bash scripts/verify_sprint281.sh
bash scripts/verify_sprint28.sh
bash scripts/verify_sprint26.sh
```

## Sprint 2.8

```bash
cd /home/jb/dev/hydra
python3 -m py_compile app/kit_covers.py app/aesthetica.py
wsl -d Ubuntu -u root -- bash -lc 'chown -R jb:jb /home/jb/dev/hydra/products/product_43'
python3 scripts/build_product43_kit.py --covers-only
chmod +x scripts/verify_sprint28.sh
bash scripts/verify_sprint28.sh
docker compose up -d --build hydra-console
LIVE=1 bash scripts/verify_sprint28.sh
bash scripts/verify_sprint26.sh
bash scripts/verify_sprint25.sh
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
