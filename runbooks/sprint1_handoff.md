# Sprint 1.1 Handoff

## What Was Built

- Docker Compose stack with Postgres 16, Redis 7, and the HYDRA FastAPI console.
- FastAPI routes for health, opportunity listing, mock SIGNAL scan, operator approval, product listing, and product creation.
- Automatic database table creation on app startup.
- Deterministic SIGNAL scoring in `app/signal_engine.py`.
- Mock opportunity candidates with realistic public-signal evidence.
- Ruflo bridge prompt builders for product planning and listing copy.
- Product edit flow for title, format, price, status, Gumroad URL, and notes.
- Manual revenue ledger with total revenue, product totals, and individual events.
- Settings page with kill switch and daily budget controls.
- Mock SIGNAL scan deduplication by source, topic, and vertical.
- HTTP Basic Auth for all routes except `/health`.
- Ruflo artifact import for outline, product content, listing copy, QA review, and distribution posts.
- Run scripts for local startup, shutdown, mock seeding, Ruflo install, and future VPS bootstrap.
- Runbooks for launch day, Ruflo boundaries, and this handoff.

## How To Run

```bash
cd /home/jb/dev/hydra
chmod +x scripts/*.sh
./scripts/dev_up.sh
curl http://localhost:8000/health
python3 scripts/seed_mock_signals.py
python3 scripts/seed_mock_signals.py
```

Open:

```text
http://localhost:8000
```

Login with `admin / change-me` unless overridden by environment variables.

## What Is Missing

- Real Reddit, Product Hunt, Google Trends, or marketplace scrapers.
- Real Gumroad API integration.
- Automated revenue ingestion.
- Kill switch enforcement beyond visible state and helper functions.
- Budget cap enforcement beyond visible state and helper functions.
- User accounts or OAuth.
- Ruflo execution automation.
- Migrations beyond startup table creation.

## Next Tasks For Claude

- Enforce kill switch before any publish/spend route exists.
- Enforce daily budget before any paid API or ad workflow exists.
- Add one real public-signal collector behind a manual button.
- Add product artifact export/download if useful for packaging.
- Add product package file tracking.
- Add Gumroad URL validation and live/listed status guidance.
- Replace Basic Auth before exposing the console beyond a trusted private environment.
- Convert startup table creation to Alembic once schema changes become frequent.


# Sprint 1.2 Handoff

## What Was Added

- Auto-prefilled draft product on opportunity approval (title, format, price hint, structured notes — operator edits before generation).
- Approve now redirects to the new product's edit page instead of back to the list.
- New `product_files` table and routes for tracking local package paths (ZIP/PDF/Markdown). No file upload.
- Artifact export route `POST /products/{id}/artifacts/export` writes one Markdown file per artifact under `exports/product_<id>/NNN_<type>_<slug>.md`.
- HackerNews collector `POST /opportunities/collect/hn` (Algolia public API) inserts scored candidates with cross-source-confirmation set low (single source).
- `assert_system_can_act(action_name)` helper. Used to gate HN collection and artifact export. Returns HTTP 423 with `{"blocked": true, ...}` when the kill switch is active.
- New `GET /launch` dashboard with approved/products/live counts, missing-URL list, manual revenue total, kill-switch and budget readout, top 5 opportunities, latest 5 products.
- Gumroad URL warnings on the product edit page: missing-URL when `live`, malformed when not http(s), green "Launch URL ready." when `live` + URL present.
- Kill-switch banner on the Opportunities page when active.
- New `Launch` nav link.
- `httpx` added to `requirements.txt`.
- `./exports` host directory mounted into the console container at `/app/exports`.

## How To Run

```bash
cd /home/jb/dev/hydra
chmod +x scripts/*.sh
./scripts/dev_up.sh
curl http://localhost:8000/health
python3 scripts/seed_mock_signals.py
```

Then open `http://localhost:8000/launch` to see the dashboard, or `http://localhost:8000/opportunities` to scan signals.

## What Is Still Missing

- Real Reddit, Product Hunt, Google Trends, or marketplace scrapers (only mock + HN).
- Real Gumroad API integration / automated publishing.
- Automated revenue ingestion.
- Budget cap enforcement beyond visible state.
- OAuth / multi-user accounts.
- Background scheduling (HN runs only on operator click).
- Alembic migrations.

## Recommended Sprint 1.3

- Add a second real collector (Product Hunt or Reddit) behind a button.
- Persist source weights in the DB and update them based on revenue attribution.
- LLM-backed prefill: replace the deterministic notes block with one Haiku/4o-mini call per approval, gated by daily budget. Falls back to deterministic on failure or when kill switch is on.
- Move basic auth to a session login + optional OAuth.
- Add Alembic and convert `init_db()` to migrations.
- Add Gumroad listing draft via API (still operator-publishes manually).
- Auto-refresh `/launch` every 60s (HTMX polling).
