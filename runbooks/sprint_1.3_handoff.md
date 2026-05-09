# Sprint 1.3 Handoff — Launch Learning v1

**Sprint:** 1.3
**Branch:** uncommitted on `main` (sprint not yet committed/tagged at write time)
**Started:** 2026-05-08
**Completed:** 2026-05-08
**Executor:** Claude (with operator approval of pivot from original LLM-execution-layer plan)
**Boundary touched:** no — Zone A code unchanged
**Spend touched:** no — no new LLM calls, no money paths

---

## 1. Inspection summary

Read at start: `runbooks/ROADMAP.md`, `runbooks/SESSION_RECOVERY.md`, `runbooks/sprint1_handoff.md` (Sprint 1.1 + 1.2), `runbooks/known_issues.md`, `runbooks/verification_results.md`, `runbooks/commands_run.md`, `logs/sprints/sprint_history.md`, `logs/verification/verification_history.md`, `logs/runtime/runtime_events.jsonl`, `logs/revenue/revenue_events.jsonl`, `app/main.py`, `app/db.py`, `README.md`.

Verified state at start: stack healthy (Postgres + Redis + FastAPI all green), product 35 (`AI Coding Agent Safety Pack` → `Cheat Sheet Pdf: SafeSandbox – infinite undo for AI coding agents (...)`) live on Gumroad with 5 artifacts but **0 product_files rows and 0 revenue events**, 31 candidates in `new` status, 3 in `approved`. Continuity infra (preflight, status_snapshot, sprint_closeout, validate_env, ledgers, SESSION_RECOVERY.md) all present and PASS.

## 2. Objective (approved deviation from original ROADMAP.md)

The roadmap's Sprint 1.3 was "Controlled LLM Execution Layer." Pivoted with operator approval to **Sprint 1.3 — Launch Learning v1** because the binding constraint after product 35's launch is *attribution*, not LLM plumbing. Reasoning logged in the chat session prior to implementation.

Approved features: attribution, launch tracking, title cleanup, lightweight HN classifier, product_files auto-registration, distribution post tracking. Rejected: LLM execution layer, new collectors, orchestration, autonomous posting, analytics dashboard.

## 3. Files changed

### Modified
- `app/db.py` — added attribution columns on `RevenueEvent` and `ProductArtifact`; added `_apply_one_shot_migrations()` running idempotent `ALTER TABLE ADD COLUMN IF NOT EXISTS` until Alembic lands in 2.0.
- `app/main.py` — replaced `f"{fmt.title()}: ..."` title prefill with `f"{topic} — {short_label}"` via new `_format_short_label()`; added keyword-based `_hn_classify()` and wired it into `_hn_to_candidate`; auto-register `product_files` rows on `POST /products/<id>/artifacts/export`; new `POST /products/<id>/artifacts/<aid>/publish`; extended `POST /revenue` with `source_attribution` + `channel_tag`; widened `/launch` route to compute channel rollup + missing-distribution list.
- `app/templates/product_edit.html` — per-`distribution_post` artifact: shows publish status banner + form to record `published_url` + `channel_tag`.
- `app/templates/revenue.html` — form gains `channel_tag` + `source_attribution` fields; events table gets an Attribution column.
- `app/templates/launch.html` — adds "Live without distribution" metric, "Revenue by channel" rollup table, "Live products with no published distribution post" list.

### Created
- `.gitignore` — covers `.env`, `__pycache__/`, `ruflo/`, `products/`, `exports/product_*/` (preserves `exports/.gitkeep`), `backups/`, dump files, OS/editor noise.
- `scripts/verify_sprint13.sh` — 13 assertions covering schema migrations, title prefill, classifier, file auto-registration + idempotency, publish flow + URL validation, revenue attribution, launch dashboard rendering.
- `scripts/state_inspect.sh` — read-only one-shot recovery check (used during inspection, retained for future sessions).

### Deleted
- None.

## 4. Schema changes

Five additive columns via idempotent SQL on startup. Re-running `init_db()` is safe (`IF NOT EXISTS`).

```sql
ALTER TABLE revenue_events    ADD COLUMN IF NOT EXISTS source_attribution TEXT;
ALTER TABLE revenue_events    ADD COLUMN IF NOT EXISTS channel_tag        TEXT;
ALTER TABLE product_artifacts ADD COLUMN IF NOT EXISTS published_url      TEXT;
ALTER TABLE product_artifacts ADD COLUMN IF NOT EXISTS published_at       TIMESTAMP;
ALTER TABLE product_artifacts ADD COLUMN IF NOT EXISTS channel_tag        TEXT;
```

A unique index on `product_files(product_id, file_path)` was attempted and reverted because legacy rows from Sprint 1.2 verification runs trip it. **Carry forward to Sprint 2.0 (Alembic) with a paired dedupe migration.**

## 5. Commands run

```bash
docker compose up -d --build
docker compose logs --tail 60 hydra-console
scripts/verify_sprint13.sh
python3 -m py_compile app/main.py app/db.py app/signal_engine.py app/ruflo_bridge.py
```

## 6. Verification results

`scripts/verify_sprint13.sh` — **ALL PASS** (13/13). Detailed checks logged in `runbooks/verification_results.md`.

- Stack: `/health` 200.
- Migrations: all 5 columns exist on the running DB.
- Title prefill: approved candidate 43 produced product 36 with title `"Show HN: GETadb.com – every GET request creates a DB — Cheat Sheet"` (no `Pdf:` prefix).
- HN classifier: `"Show HN: cline-style AI coding agent for Cursor"` → `("AI coding tools", "cheat sheet PDF")`.
- File auto-registration: product 35 went from 0 → 5 `product_files` rows; second export idempotent (`files_registered=0`).
- Publish flow: well-formed URL stored; `not-a-url` rejected 400.
- Revenue attribution: `channel_tag=twitter` stored alongside the sale row.
- Launch dashboard: "Revenue by channel" + "Live without distribution" sections render.

Spend during verification: $0.00 (no new LLM calls).

## 7. Known issues

Carried forward to `runbooks/known_issues.md`:

- 2026-05-08 [sprint 1.3] **medium** — duplicate rows exist in `product_files` (product 34, `products/test/test.zip`) from Sprint 1.2 verification runs. Blocks the unique-index migration. Resolve in Sprint 2.0 with a paired dedupe.
- 2026-05-08 [sprint 1.3] **low** — title prefill is now `f"{topic} — {short_label}"`. Long topics still truncate at 70 chars; the truncation can lop off useful context. Acceptable; revisit with LLM prefill in Sprint 1.4.
- 2026-05-08 [sprint 1.3] **low** — `_hn_classify` is a 11-rule keyword router. False negatives are likely on novel topics; default falls back to "AI tools / cheat sheet PDF." Acceptable; will be replaced in Sprint 1.4 by an LLM classifier.
- 2026-05-08 [sprint 1.3] **low** — channel rollup groups by raw `channel_tag`. Operator typos like `Twitter` vs `twitter` will appear as separate rows. Mitigation: `_attribution_lower()` lowercases on insert; rely on operator discipline for now.

## 8. Rollback procedure

Code rollback (single file revert):

```bash
# Drop new routes / template blocks by reverting just three files
git checkout HEAD -- app/main.py app/db.py app/templates/product_edit.html app/templates/revenue.html app/templates/launch.html
docker compose up -d --build
```

Schema rollback (only if mandatory; new columns are nullable and harmless if left in place):

```sql
ALTER TABLE revenue_events    DROP COLUMN IF EXISTS source_attribution;
ALTER TABLE revenue_events    DROP COLUMN IF EXISTS channel_tag;
ALTER TABLE product_artifacts DROP COLUMN IF EXISTS published_url;
ALTER TABLE product_artifacts DROP COLUMN IF EXISTS published_at;
ALTER TABLE product_artifacts DROP COLUMN IF EXISTS channel_tag;
```

Auto-registered `product_files` rows for existing products can be deleted (export remains the source of truth for the files on disk).

## 9. Boundary review

- [x] No new code path exposes marketplace credentials to Zone A.
- [x] No new code path lets Zone A publish, spend, or modify state.
- [x] No new code path automates posting in a moderated community. The publish form *records* a manual post; it does not perform one.
- [x] No new code path adds an LLM call. Sprint 1.3 deliberately introduces zero new LLM surface.

## 10. Spend review

- Daily budget cap: unchanged at `$3` (informational; no LLM paths exist yet).
- Total spend during sprint: `$0.00`.
- New routes that can spend: none.
- New routes gated by `assert_system_can_act`: none added (existing artifact export and HN collect remain gated).

## 11. Operator-facing changes

- Approve now produces titles like `"Topic name — Cheat Sheet"` instead of `"Cheat Sheet Pdf: Topic name"`.
- Approving a fresh HN candidate routes it to a more specific vertical/format pair via the keyword classifier.
- Product edit page shows a publish form below each `distribution_post` artifact. Operator records the URL of where the launch post went after posting it manually.
- Revenue form has new `channel_tag` and `source_attribution` fields. Use `twitter`, `reddit`, `hn`, `blog`, etc. as the tag.
- Launch dashboard shows "Revenue by channel," "Live without distribution," and the metric "Live without distribution" alongside the existing dashboard cards.

## 12. Recommended next sprint

**Sprint 1.4 — Controlled LLM Execution Layer (the originally-planned 1.3).**

Rationale: with attribution data now flowing, an LLM client is the next step that compounds value. The existing keyword classifier is deliberately limited; an LLM classifier multiplies signal triage throughput. The `evidence` field can finally be turned into prefilled listing copy. Sprint 1.4 should include `app/llm.py` with daily-budget enforcement, a `llm_calls` cost ledger, and replacements for `build_default_product_fields` notes block + `_hn_classify`. See "Sprint 1.4 plan" at the bottom of `runbooks/ROADMAP.md` (will be appended).

Blocking issues for 1.4: none. Open hazards from 1.3 (legacy duplicate `product_files` rows) do not block; clean up alongside Alembic in Sprint 2.0.

## 13. Session-recovery paragraph

> I read the handoff for Sprint 1.3. State: stack healthy, product 35 live, 5 product_files now auto-registered for product 35, attribution columns live and tested, distribution publish flow tested, channel rollup rendering. The next sprint per the roadmap is Sprint 1.4 (Controlled LLM Execution Layer) — i.e., the originally-planned Sprint 1.3 — because attribution is now flowing and an LLM client is the next compounding lever. Open hazards: legacy `product_files` duplicate (medium, deferred to 2.0), no nightly DB backup, container still runs as root. I am cleared to start: Sprint 1.3 handoff complete, all 13 verifications green, no boundary or spend regressions.
