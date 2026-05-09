# Sprint 1.6 Handoff — Alembic + Backups + Listings Table

**Sprint:** 1.6  
**Status:** Complete  
**Date:** 2026-05-09  
**Implemented by:** Claude (Chief Architect / Lead Engineer)  
**Next sprint:** 1.7 — see `runbooks/sprint_1.7_codex_brief.md`

---

## What This Sprint Delivers

| Deliverable | Purpose |
|---|---|
| Alembic migration management | Schema discipline — no more `create_all()` footguns |
| `listings` table | Multi-platform listing state tracker (Sprint 4.0 API publish ready) |
| `backup_db.sh` / `restore_db.sh` | Pre-launch operational safety net |
| `scripts/verify_sprint16.sh` | 30-check acceptance gate |

---

## Files Changed

### New files
```
app/alembic.ini                              Alembic config (sqlalchemy.url overridden in env.py)
app/alembic/__init__.py                      Package marker
app/alembic/env.py                           Imports db.Base + DATABASE_URL; runs online/offline migrations
app/alembic/script.py.mako                   Standard Alembic migration template
app/alembic/versions/0001_baseline.py        Baseline: all 8 Sprint 1.4 tables
app/alembic/versions/0002_sprint16_listings.py  Adds listings table + unique index
scripts/backup_db.sh                         pg_dump → gzip into backups/
scripts/restore_db.sh                        Confirmed destructive restore from .sql.gz
scripts/verify_sprint16.sh                   30 acceptance checks
runbooks/sprint_1.6_handoff.md              This file
runbooks/sprint_1.7_codex_brief.md          Next sprint spec (Codex-ready)
```

### Modified files
```
app/requirements.txt    Added alembic==1.13.3
app/db.py               Added _APP_DIR, Listing model, replaced init_db() with Alembic 3-case logic
app/main.py             Imported Listing, added listings query to edit_product
app/templates/product_edit.html   Added Listings section (read-only tracker)
```

---

## Architecture: Alembic Integration

### `init_db()` — 3-case logic

```
At startup → engine.connect() → inspect tables
   │
   ├─ has_our_tables AND NOT has_alembic_version
   │    → Pre-Alembic DB: stamp head (no re-run, no data loss)
   │
   └─ everything else
        → command.upgrade("head")  ← Fresh: creates all; Managed: upgrades to latest
```

`_apply_one_shot_migrations()` is kept for transition safety — it runs AFTER Alembic so any new ADD COLUMN IF NOT EXISTS statements remain idempotent.

### Zone A / Zone B boundary unchanged

Listing records are written by Zone B (FastAPI endpoints) only. Zone A (LLM generation) never reads marketplace credentials or writes directly to `listings`. Sprint 4.0 will add API publish routes that create/update Listing rows.

---

## Listing Model

```python
class Listing(Base):
    __tablename__ = "listings"
    id          = Integer PK
    product_id  = FK → products.id (CASCADE DELETE)
    platform    = Text  # gumroad | etsy | sellfy | payhip | creative_market
    status      = Text  # draft | live | paused | archived
    external_id = Text  # marketplace-assigned ID once published
    draft_url   = Text
    live_url    = Text
    price_cents = Integer
    currency    = Text  (default: USD)
    notes       = Text
    created_at  = DateTime
    updated_at  = DateTime (auto onupdate)

UNIQUE INDEX: (product_id, platform)  → one listing per product per marketplace
```

---

## Running Verification

### Static checks (no DB required)
```bash
cd /home/jb/dev/hydra
bash scripts/verify_sprint16.sh
# Expect: 28 PASS, 0 FAIL, 3 SKIP
```

### Full checks (live DB)
```bash
cd /home/jb/dev/hydra
docker compose up -d
LIVE_DB=1 bash scripts/verify_sprint16.sh
# Expect: 31 PASS, 0 FAIL, 0 SKIP
```

---

## Backup Operations

### Take a backup
```bash
# From host (requires psql client):
bash scripts/backup_db.sh

# From inside docker compose (no host psql needed):
docker compose exec db pg_dump -U hydra hydra | gzip > backups/hydra_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore from backup (⚠️ destructive)
```bash
bash scripts/restore_db.sh backups/hydra_20260509_120000.sql.gz
# Prompts: "Type YES to continue"
```

Backups land in `backups/` at project root. Add to `.gitignore` if not already excluded.

---

## First-Run Transition (Pre-Alembic DB)

If the DB already has HYDRA tables from a previous sprint (no `alembic_version` table):

```bash
# init_db() auto-detects and stamps — nothing to do manually.
# To verify after restart:
docker compose exec hydra-console alembic -c app/alembic.ini current
# Should print: 0002 (head)
```

If you need to force-stamp manually:
```bash
docker compose exec hydra-console \
    alembic -c app/alembic.ini stamp head
```

---

## Boundary Review

| Check | Status |
|---|---|
| Marketplace credentials in Zone A? | ✗ No — listings table is Zone B only |
| LLM calls gated by kill switch + budget? | ✓ Unchanged from Sprint 1.5 |
| `_apply_one_shot_migrations()` still runs? | ✓ Yes — after Alembic upgrade for safety |
| Fresh DB brings up full schema? | ✓ 0001 + 0002 migrations create all 9 tables |
| Pre-Alembic DB safe on upgrade? | ✓ 3-case logic stamps without re-running |

---

## Known Issues / Carry-Forward

1. **`onupdate=func.now()` for `listings.updated_at`** — SQLAlchemy's `onupdate` works for ORM updates but not raw SQL. A future migration can add a Postgres trigger if needed for Sprint 4.0 API writes.
2. **No API publish routes yet** — `listings` table is read-only from the UI. Sprint 4.0 adds `POST /products/{id}/listings/{platform}/publish`.
3. **`backups/` directory** — ensure it is in `.gitignore`. Database backups should not be committed.

---

## Sprint 1.5 → 1.6 → 1.7 Critical Path

```
1.5 (complete) In-Process Agentic Generation (5 routes, multi-marketplace listing copy)
1.6 (complete) Alembic + Backups + Listings Table
1.7 (next)     Reddit Collector + Celery Scheduler (automated signal pipeline)
```

See `runbooks/ROADMAP.md` — critical path section for full sequence to Sprint 5.0.
