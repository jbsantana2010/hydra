# Verification Results

Append-only summary of what was verified, with timestamps. One entry per sprint completion (or per major mid-sprint validation).

---

## Sprint 1.2 — 2026-05-08

| Check | Result |
|---|---|
| `curl /health` | 200 `{"status":"healthy"}` |
| Mock SIGNAL scan idempotent | inserted 0, skipped 12 on second run |
| HN collect (query=`AI agents`) | fetched 12, scored 12, inserted 12 |
| Approve auto-prefill | 303 → `/products/<new_id>/edit` with prefilled title/format/price/notes |
| Approve idempotency | re-approving same candidate returns existing product, no duplicate |
| Add file record | 303; row visible on edit page |
| Add artifact | 303; row visible on edit page |
| Artifact export | wrote `001_<type>_<slug>.md` under `./exports/product_<id>/` on the host |
| Kill switch blocks HN collect | HTTP 423 + `{"blocked":true,...}` |
| Kill switch blocks artifact export | HTTP 423 + `{"blocked":true,...}` |
| URL warning: `live` + empty | warn banner "Live status set without a Gumroad URL." |
| URL warning: malformed | warn banner "must start with http:// or https://" |
| URL warning: healthy | good banner "Launch URL ready." |
| Launch dashboard renders | 200 with all metric cards present |


## Sprint 1.3 — 2026-05-08

| Check | Result |
|---|---|
| `curl /health` | 200 `{"status":"healthy"}` |
| `revenue_events.source_attribution` exists | PASS |
| `revenue_events.channel_tag` exists | PASS |
| `product_artifacts.published_url` exists | PASS |
| `product_artifacts.published_at` exists | PASS |
| `product_artifacts.channel_tag` exists | PASS |
| Title prefill no longer prefixes `Cheat Sheet Pdf:` | PASS — produced `Show HN: GETadb.com – every GET request creates a DB — Cheat Sheet` |
| HN classifier routes coding-agent titles → `(AI coding tools, cheat sheet PDF)` | PASS |
| Artifact export registers `product_files` rows | PASS — 5 rows added on first export of product 35 |
| Artifact export idempotent on second run | PASS — `files_registered=0` on re-run |
| Distribution publish stores `channel_tag` | PASS — `twitter` recorded |
| Malformed publish URL rejected | PASS — HTTP 400 |
| Revenue with attribution stored | PASS — `channel_tag=twitter` on event |
| Launch dashboard renders "Revenue by channel" | PASS |
| Launch dashboard renders "Live without distribution" | PASS |


## Sprint 1.5 — 2026-05-09

| Check | Result |
|---|---|
| Sprint 1.5 imports + reverse_providers param | PENDING — run verify_sprint15.sh |
| /health 200 | PENDING |
| Kill switch blocks all 5 generation routes | PENDING |
| budget=0 blocks all 5 generation routes | PENDING |
| Prerequisite gates (content/listing/qa/distribution without prior step) | PENDING |
| outline returns blocked/failed without API keys (no crash) | PENDING |
| product_edit shows all 5 generation buttons | PENDING |
| product_edit shows all 4 storefronts (Gumroad · Etsy · Sellfy · Payhip) | PENDING |
| Existing /products /revenue /launch /settings routes | PENDING |

_Run `./scripts/verify_sprint15.sh` and replace PENDING with PASS/FAIL._

---

## Sprint 1.4 — 2026-05-09

| Check | Result |
|---|---|
| `python3 -m py_compile app/main.py app/db.py app/llm.py` | PASS |
| `./scripts/dev_up.sh` | PASS |
| `scripts/verify_sprint14.sh` | PASS |
| App imports | PASS — `main`, `llm`, `db.LlmCall` import cleanly |
| `llm_calls` table columns | PASS — id, provider, model, purpose, prompt/completion tokens, cost, duration, status, error, created_at |
| `/health` | PASS |
| Settings LLM spend readout | PASS |
| Settings recent LLM calls table | PASS |
| Kill switch blocks `llm_call` | PASS — `LlmBlocked`, row logged |
| `daily_budget_usd=0` blocks `llm_call` before provider call | PASS — `LlmBlocked`, row logged |
| API-key-free local fallback | PASS — no route crash without keys |
| HN classifier fallback | PASS |
| HN collection without keys | PASS — returned HackerNews JSON using fallback classification |
| Product approval prefill without keys | PASS — draft product created with deterministic notes |
| Existing Products/Revenue/Launch routes | PASS |

---

## Sprint 1.7 — 2026-05-10

| Check | Result |
|---|---|
| OneDrive Sprint 1.7 files merged into WSL source of truth | PASS |
| `python3 -m py_compile app/main.py app/db.py app/llm.py` | PASS |
| Container py_compile for `main.py`, `db.py`, `llm.py` | PASS |
| Alembic upgrade to `0003` | PASS |
| Alembic current | PASS — `0003 (head)` |
| `./scripts/preflight_check.sh` | PASS |
| `bash scripts/verify_sprint17.sh` | PASS — 30/30 |
| `LIVE=1 bash scripts/verify_sprint17.sh` | PASS — 38/38 |
| `bash scripts/verify_sprint16.sh` | PASS — 43/43, 3 optional LIVE_DB checks skipped |
| `bash scripts/verify_sprint15.sh` | FAIL — preexisting generation guard-path verifier failures |
| Manual CSV import | PASS — 10 items imported from `scripts/sample_research.csv` |
| Manual pattern extraction | PASS — 13 market patterns created |
| Manual opportunity generation | PASS — 5 pending-review candidates created |

---

## Sprint 1.8 — 2026-05-10

| Check | Result |
|---|---|
| `./scripts/preflight_check.sh` | PASS |
| `bash scripts/verify_sprint17.sh` | PASS |
| `LIVE=1 bash scripts/verify_sprint17.sh` | PASS |
| `python3 -m py_compile app/main.py app/db.py app/llm.py` | PASS |
| `bash scripts/verify_sprint18.sh` | PASS — 7/7 |
| `LIVE=1 bash scripts/verify_sprint18.sh` | PASS — 17/17 |
| Product 43 package route | PASS — 303 success redirect |
| Product 43 ZIP | PASS — `products/product_43.zip` |
| Product 43 printable HTML | PASS — generated under `products/product_43/printable/` |
| Product 43 source Markdown | PASS — generated under `products/product_43/source/` |
| Product 43 manifest/checklist/README | PASS |
| Product 43 `product_files` package row | PASS |
