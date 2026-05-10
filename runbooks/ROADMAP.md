# HYDRA Master Roadmap

**Authoritative execution plan from current state to first real autonomous revenue loop.**

- **Owner:** Operator (jb)
- **Last updated:** 2026-05-08, end of Sprint 1.2
- **Boundary law:** Zone A (Ruflo/Claude/Codex) generates artifacts only. Zone B (FastAPI + Postgres + Redis) owns approvals, state, money, URLs, budgets, and publishing authority.
- **Resilience target:** Any agent (Codex, Claude, ChatGPT, future contributor) must be able to resume HYDRA from the last sprint handoff without re-deriving context.

## Table of contents

1. [Current state audit](#part-1--current-state-audit)
2. [Master roadmap](#part-2--master-roadmap)
3. [Critical path](#part-3--critical-path)
4. [Task classification](#part-4--task-classification)
5. [Operational continuity system](#part-5--operational-continuity-system)
6. [Risk register](#part-6--risk-register)
7. [First real revenue plan](#part-7--first-real-revenue-plan)
8. [Long-term architecture guardrails](#part-8--long-term-architecture-guardrails)
9. [Execution priorities](#part-9--execution-priorities)


---

## Part 1 — Current state audit

### Production-ready

Nothing yet. HYDRA is a local-only operator console with no public surface and no real money flow.

### MVP-ready (good enough for tonight's first launch)

- Docker Compose stack: Postgres 16, Redis 7, FastAPI console behind HTTP basic auth.
- `/health` endpoint, basic-auth middleware, default admin/change-me.
- Database models: `OpportunityCandidate`, `Product`, `ProductArtifact`, `ProductFile`, `RevenueEvent`, `Approval`, `SystemFlag`. Tables auto-created via `Base.metadata.create_all()` on startup.
- Mock SIGNAL pipeline with 12 deterministic candidates and idempotent dedup by (source, topic, vertical).
- Deterministic SIGNAL scoring formula in `app/signal_engine.py` (0-100, weighted six components minus two penalties).
- HackerNews collector: `POST /opportunities/collect/hn` against the Algolia public API. Conservative defaults; cross-source-confirmation deliberately low.
- Operator approval flow: `POST /opportunities/{id}/approve` auto-creates a draft `Product` with prefilled title, format, price, structured notes, then redirects to its edit page.
- Manual revenue ledger with totals and per-product rollup.
- Kill switch + daily budget settings.
- `assert_system_can_act()` guard. Used by HN collector and artifact export. Returns HTTP 423 + `{"blocked":true,...}` when on.
- Artifact storage (`POST /products/{id}/artifacts`) and Markdown export (`POST /products/{id}/artifacts/export`) writing to `./exports/product_<id>/` (host-mounted volume).
- Product file path tracking (`product_files` table — paths only, no upload).
- Launch dashboard at `/launch` with approved/products/live counts, missing-URL list, top opportunities, latest products, kill-switch and budget readouts.
- Gumroad URL warnings on the product edit page (live without URL, malformed URL, healthy URL).
- Ruflo bridge prompts for product planning and listing copy (paste-driven; no Ruflo execution yet).
- Runbooks: `sprint1_handoff.md`, `launch_day.md`, `ruflo_boundary.md`. Verification scripts: `scripts/verify_sprint12.sh`, `scripts/verify_url_warnings.sh`.

### Still mock or demo

- SIGNAL is still seeded by `signal_engine.MOCK_CANDIDATES` for non-HN sources. No Reddit, Product Hunt, Google Trends, YouTube, AI-tool-directory collectors.
- Cross-source confirmation is a static value per record, not computed by clustering.
- Ruflo "automation" is operator-driven copy/paste — no Ruflo subprocess invocation, no programmatic prompt → artifact loop.
- Source weights do not exist. Revenue does not feed back into SIGNAL scoring.
- No real Gumroad API integration. Listing live = operator pastes URL by hand.
- No automated revenue ingestion. Revenue events are typed in.
- No background scheduling. Every collection runs only on operator click.
- No retry/DLQ infrastructure (the few worker-shaped routes are synchronous).
- No analytics beyond raw counts.

### Technical debt

| Item | Severity | Notes |
|---|---|---|
| `init_db()` runs `create_all()` on startup; no Alembic | Medium | Fine for additive tables; column changes will require manual migrations or destructive resets. Pay down at the start of Sprint 2.0. |
| HTTP basic auth, single user | Medium | OK on localhost; unacceptable on a public VPS. Block any cloud exposure on this. |
| Container runs as root; exported files land as root on host | Low-Medium | Annoyance, not a security issue locally. Fix in Sprint 1.3 with a non-root user in the Dockerfile. |
| No CSRF protection on POSTs | Low (local) / High (public) | Tied to auth upgrade. |
| Inline CSS in `base.html` | Low | Acceptable; defer until templates need a real refactor. |
| No structured logging | Medium | Print statements only. Add `structlog` in Sprint 2.x. |
| No tests beyond verification scripts | Medium | Add pytest harness in Sprint 2.x. |
| Two `_valid_basic_auth` defs were briefly created during 1.2 implementation, fixed before commit | Low | Watch for shell-quoting / edit-block hazards in future sprints. |

### Operational risks (current)

- **API spend runaway** when LLM calls land in main.py. Mitigation: spend caps required before any LLM-calling route ships.
- **Marketplace ban** if product listings start looking like spam. Mitigation: hard cap (≤ 3 listings/day) + manual publish + AI disclosure.
- **Schema drift** from `create_all()` once columns change. Mitigation: Alembic baseline at start of Sprint 2.0.
- **Container-as-root** complicates future hardening. Mitigation: non-root user in Sprint 1.3.
- **No backups.** A `docker volume rm` would erase everything. Mitigation: nightly `pg_dump` to host disk in Sprint 2.0.

### Architectural risks

- **Ruflo dependency drift.** Ruflo ships near-daily. Pin a tag and vendor a fork before any Sprint 3.x work depends on it.
- **Boundary erosion.** Easy to slip Gumroad credentials into a generated agent prompt "for convenience." Mandatory boundary review at the end of every sprint with a Zone A change.
- **Premature scaling.** Adding Kubernetes, Temporal, microservices, or a vector DB at this stage will sink the project. Block any such proposal until the sprint that justifies it.
- **Single VPS / single Compose stack** is fragile but appropriate at this size. Plan failover (off-host backups + bootstrap script) before plan HA.

### Do not touch yet

- The `Approval` table — needs to remain append-only audit log even if it duplicates rows.
- The deterministic scoring formula in `signal_engine.calculate_score()` — until source weights and revenue attribution are in place, swapping it for ML is premature.
- The Ruflo bridge prompt builders — they encode the boundary contract. Touch only with explicit boundary review.
- HTTP basic auth removal — will break the verification scripts and seed_mock_signals.py. Replace, don't rip out.


---

## Part 2 — Master roadmap

Phases compressed into the smallest sequence that closes the loop:

```
1.x Launch-support MVP   →  2.x Real signal intel  →  3.x Product automation
4.x Distribution + attribution  →  5.x Feedback learning loop
6.x Semi-autonomous operation   →  7.x Multi-marketplace expansion
```

Sprint duration assumes one focused operator working ~3 hours/day. Compress aggressively if more time is available, but never compress acceptance criteria.

### Sprint metadata legend

- **Complexity:** S = ≤ 4 hours · M = 1 day · L = 2-3 days · XL = > 3 days
- **Launch impact:** how much it changes user-visible behavior
- **Executor:** **Codex-safe** = boilerplate Codex can land without architectural drift. **Claude-required** = architecture / prompt engineering / signal strategy. **Human-required** = real-world account, money, or judgment call
- Dependencies are listed by sprint id (e.g. `1.3`); sprints with no dependency line have none beyond the previous sprint

---

### Sprint 1.2 — Launch-support MVP (DONE)

Already shipped: file tracking, artifact export, Gumroad URL warnings, launch dashboard, HN collector, kill-switch enforcement, auto-prefill on approval.

---

### Sprint 1.3 — Tightening before automation

- **Objective:** Pay down the most expensive 1.2 debt and add the LLM-backed prefill the operator already requested.
- **Features:**
  - Non-root user in the FastAPI Dockerfile so exports land as `jb:jb`.
  - `app/llm.py` thin client (Anthropic Haiku + OpenAI 4o-mini) with hard per-call spend cap, daily total cap (reads `daily_budget_usd`), structured logging, kill-switch check.
  - Replace `build_default_product_fields()` notes block with one Haiku call gated by `daily_budget`. Falls back to the existing deterministic block on failure or when kill switch is on or budget is exhausted.
  - Per-call cost rows in a new `llm_calls` table (model, prompt_tokens, completion_tokens, cost_usd, agent, occurred_at).
  - Settings page shows today's spend vs cap.
  - `/launch` polls every 60s via HTMX.
- **Dependencies:** none (1.2).
- **Risks:** spend leak from a buggy retry. Mitigation: cap is enforced *before* the call, not after.
- **Complexity:** M.
- **Duration:** 1 day.
- **Tests:** unit tests for budget guard; integration test that asserts kill switch + budget zero both block a call; manual end-to-end approve → see LLM-prefilled notes.
- **Launch impact:** Low (operator UX, safer infra).
- **Rollback:** revert `app/llm.py` and `build_default_product_fields()` change; deterministic prefill resumes; no data migration needed.
- **Executor:** Codex-safe for Dockerfile + table + UI; Claude-required for prompt design and budget-guard semantics.

---

### Sprint 2.0 — Visual Commerce Generation Bridge

- **Objective:** Teach HYDRA how a winning digital product should look before any image generation exists.
- **Status:** Complete 2026-05-10.
- **Features:**
  - Visual theme intelligence by niche.
  - Aesthetic systems with palette, typography, mood, buyer signal, and avoid-list.
  - Cover/mockup prompt briefs for future image generation or Fiverr designers.
  - Product gallery planning.
  - Marketplace visual specs for Fiverr, Gumroad, Pinterest, Sellfy, and Payhip.
  - Image slot manifest.
  - Presentation hierarchy generation.
  - Manifest upgraded to `package_version: 2.0` with `visual_assets` and `visual_theme`.
- **Dependencies:** Sprint 1.9 package builder.
- **Risks:** Deterministic theme selection can be too coarse for unusual niches. Mitigation: outputs are editable specs and require human review before visual production.
- **Acceptance criteria:** `bash scripts/verify_sprint20.sh` and `LIVE=1 bash scripts/verify_sprint20.sh` pass; product 43 package contains a complete `visual/` folder.
- **Executor:** Codex-safe.

---

### Sprint 2.x — Schema discipline + backups

- **Objective:** Stop running on `create_all()` before adding any more columns.
- **Features:**
  - Alembic baseline migration covering all current tables.
  - `init_db()` rewritten to call `alembic upgrade head` instead of `create_all`.
  - `scripts/backup_db.sh` doing `pg_dump` to `./backups/YYYY-MM-DD/hydra.dump.gz` with 14-day retention.
  - `scripts/restore_db.sh` with a confirm prompt.
  - Cron entry on host (or systemd timer) running the backup nightly.
- **Dependencies:** 1.3.
- **Risks:** broken migration on first run wipes the dev DB. Mitigation: take a `pg_dump` immediately before the baseline migration; verify restore on a scratch container.
- **Complexity:** M.
- **Duration:** 1 day.
- **Tests:** restore the latest backup into a scratch Postgres and run the verification scripts against it.
- **Launch impact:** Low.
- **Rollback:** keep the pre-baseline `pg_dump`; if Alembic baseline is wrong, restore from dump and fix migration.
- **Executor:** Codex-safe.

---

### Sprint 1.8 — Product Asset Generator v1

- **Objective:** Convert generated product artifacts into real local product files and a marketplace-ready ZIP package.
- **Status:** Complete 2026-05-10.
- **Features:**
  - `POST /products/{id}/package` builds a local package from `outline`, `product_content`, and `listing_copy`.
  - Markdown source export under `products/product_<id>/source/`.
  - Printable HTML generation under `products/product_<id>/printable/` for planner/printable/worksheet/tracker/checklist formats.
  - `README.md`, `manifest.json`, and `marketplace_checklist.md`.
  - ZIP package at `products/product_<id>.zip`.
  - ZIP registration in `product_files`.
  - Product edit page includes a Package Product section and package button.
- **Dependencies:** Sprint 1.5 product generation artifacts; Sprint 1.6 product file tracking.
- **Risks:** HTML is plain and PDF conversion remains manual. Mitigation: package checklist tells the operator what still needs review/mockups/PDF conversion.
- **Acceptance criteria:** `bash scripts/verify_sprint18.sh` and `LIVE=1 bash scripts/verify_sprint18.sh` pass; product 43 packages successfully.
- **Executor:** Codex-safe.

---

### Sprint 1.9 — Commercial Presentation Packaging

- **Objective:** Make generated product packages feel commercially real and upload-ready.
- **Status:** Complete 2026-05-10.
- **Features:**
  - Cover preview HTML: `preview/cover_preview.html`.
  - Sales-page preview HTML: `preview/sales_page_preview.html`.
  - Simple local PDF export: `pdf/printable_pack.pdf`.
  - Gumroad presentation asset brief.
  - Fiverr outsourcing brief.
  - Mockup/cover specification.
  - Perceived value stack document.
  - Richer `manifest.json` tracking preview, PDF, and presentation assets.
  - Product edit copy updated to surface PDF/preview/presentation packaging.
- **Dependencies:** Sprint 1.8 package builder.
- **Risks:** PDF export is simple and text-based; preview assets are HTML specs, not generated PNG/JPG images. Mitigation: package checklist still requires human image/mockup review.
- **Acceptance criteria:** `bash scripts/verify_sprint19.sh` and `LIVE=1 bash scripts/verify_sprint19.sh` pass; product 43 package includes PDF, previews, presentation docs, and manifest metadata.
- **Executor:** Codex-safe.

---

### Sprint 2.1 — Reddit collector + scheduler

- **Objective:** Two real sources running on a schedule produce the cross-source-confirmation signal that mock candidates fake.
- **Features:**
  - `app/signal/reddit.py` using free Reddit OAuth (script app). Pulls top + new from a configurable list of subreddits and search queries.
  - APScheduler in-process or a `cron`-style worker container running mock + HN + Reddit on schedules (mock manual, HN every 30 min, Reddit every 30 min, GTrends every 6h placeholder).
  - Schedules are kill-switch-gated.
  - Settings page surfaces last-run timestamps per source.
- **Dependencies:** 2.0.
- **Risks:** Reddit OAuth token rotation. Mitigation: refresh-token store in `system_flags`.
- **Complexity:** M-L.
- **Duration:** 1-2 days.
- **Tests:** integration test against a recorded Reddit response; assert no DB write when kill switch is on.
- **Launch impact:** Medium (real candidates appear).
- **Rollback:** disable scheduler container, leave manual mock + HN buttons in place.
- **Executor:** Codex-safe for the collector; Claude-required to choose subreddits and search queries (signal strategy).

---

### Sprint 2.2 — Cross-source clustering + source weights

- **Objective:** Make the cross-source-confirmation score actually mean what it claims.
- **Features:**
  - `signals.clusters` table: clusters of candidates that the system thinks are the same opportunity.
  - Embedding-based clustering using pgvector (sentence-transformers or LLM embeddings via `app/llm.py`, daily-budget gated).
  - `cross_source_confirmation` recomputed = `min(1.0, distinct_sources_in_cluster / 3) * 100`.
  - `source_weights` table with weight 1.0 default, updated nightly from revenue attribution (placeholder until 5.x).
- **Dependencies:** 2.1.
- **Risks:** clustering false positives merge unrelated candidates and hide them. Mitigation: confidence threshold + operator-visible "merged with" link in console.
- **Complexity:** L.
- **Duration:** 2 days.
- **Tests:** synthetic candidate set with known clusters; assert recall + precision above thresholds.
- **Launch impact:** Medium (scores re-rank).
- **Rollback:** keep static cross-source values; clustering job can be paused via system flag without affecting anything else.
- **Executor:** Claude-required.

---

### Sprint 3.0 — Ruflo execution bridge

- **Objective:** Replace operator copy/paste with a controlled subprocess invocation of Ruflo or Claude Code, returning artifacts to Zone B.
- **Features:**
  - `app/zone_a/runner.py` that shells out to a pinned Ruflo / Claude Code CLI in an isolated workdir.
  - Strict allowlist of tools; no Gumroad/marketplace credentials in env.
  - Output captured into `ProductArtifact` rows with `source="ruflo:<version>"`.
  - `POST /products/{id}/generate/outline` → produces and stores an `outline` artifact.
  - Operator confirms outline before `POST /products/{id}/generate/content` runs.
  - Hard timeout, hard token cap, kill-switch check, budget cap.
- **Dependencies:** 1.3 (LLM client + budget), 2.1 (Reddit so candidates exist), 2.2 (so generated content targets clusters not raw rows).
- **Risks:** Ruflo upstream change breaks subprocess interface; secrets leak via env or stdout. Mitigations: pin Ruflo to a known good tag, vendor it; never pass marketplace creds to Zone A; redact stdout in logs.
- **Complexity:** XL.
- **Duration:** 3 days.
- **Tests:** end-to-end test producing an outline + content artifact; failure injection (Ruflo crash, timeout, oversize output).
- **Launch impact:** High (first real automation step).
- **Rollback:** `system_flag("zone_a_runner_enabled","false")` returns to copy/paste mode immediately.
- **Executor:** Claude-required.

---

### Sprint 3.1 — QA agent + content gate

- **Objective:** Stop slop. Critic LLM in a different family from the generator.
- **Features:**
  - `POST /products/{id}/generate/qa` runs an adversarial critique prompt; produces a `qa_review` artifact with structured score and blocking issues.
  - Product cannot transition `draft → generated` unless the most recent `qa_review` has `score >= threshold` and zero blocking issues, or operator overrides explicitly with a recorded reason.
  - Threshold and override settings on the Settings page.
- **Dependencies:** 3.0.
- **Risks:** false negatives waste content. Mitigation: operator override always available; tracked.
- **Complexity:** M.
- **Duration:** 1 day.
- **Tests:** seeded "bad" content trips the gate; seeded "good" content passes.
- **Launch impact:** Medium.
- **Rollback:** raise the override flag, gate becomes informational.
- **Executor:** Claude-required (prompt + threshold judgment).

---

### Sprint 3.2 — Packager

- **Objective:** Turn approved artifacts into a real shippable package on disk.
- **Features:**
  - `POST /products/{id}/package` builds a deterministic `<slug>.zip` with: PDF (Pandoc from Markdown), README, license, manifest.json. Includes any operator-attached cover image at a known path.
  - Auto-fills `product_files` rows for the resulting ZIP and PDF.
  - Versioned filenames (`<slug>-v<n>.zip`).
- **Dependencies:** 3.1.
- **Risks:** Pandoc rendering issues on weird Markdown. Mitigation: a single sanitization pass.
- **Complexity:** M.
- **Duration:** 1 day.
- **Tests:** golden-file test on a known product.
- **Launch impact:** Medium.
- **Rollback:** delete the route; manual packaging resumes.
- **Executor:** Codex-safe.

---

### Sprint 4.0 — Gumroad draft creation (no auto-publish)

- **Objective:** First real Zone B credential touching a marketplace, behind a hard HITL gate.
- **Features:**
  - `app/integrations/gumroad.py` using single-user OAuth token in `system_flags` (encrypted at rest if practical, otherwise in `.env` only).
  - `POST /products/{id}/listing/draft` creates a draft listing on Gumroad, uploads the package, sets price, tags, description from the `listing_copy` artifact, stores returned URL.
  - Listing remains in Gumroad's draft state — operator clicks publish in Gumroad UI manually.
  - Idempotency: a successful draft sets `Product.gumroad_draft_id`; re-runs update the existing draft instead of creating a new one.
- **Dependencies:** 3.2 (need a package to upload).
- **Risks:** Gumroad token leaks; runaway loop creates 100 drafts. Mitigations: token only on VPS env, never in repo; idempotency key on the listing call; rate limit (1 draft/minute, 5/day).
- **Complexity:** L.
- **Duration:** 2 days.
- **Tests:** mocked Gumroad API tests for retry/idempotency; one real call against the operator's sandbox shop.
- **Launch impact:** High (first real path to public listing).
- **Rollback:** flip `system_flag("gumroad_drafts_enabled","false")`; existing drafts stay safe in Gumroad.
- **Executor:** Claude-required for design; Codex-safe for the API client once the design is in place.

---

### Sprint 4.1 — Owned-channel distribution drafts

- **Objective:** AI drafts launch posts; operator publishes manually.
- **Features:**
  - `POST /products/{id}/distribute/drafts` produces N posts targeted to the candidate's `audience_locations`. Stored as `distribution_post` artifacts.
  - Posts are NOT sent anywhere automatically. Operator copies them.
  - Optional: schedule to operator-owned Twitter/Buffer queue via the operator's API key (still HITL — schedule != send).
- **Dependencies:** 3.0, 4.0.
- **Risks:** auto-posting drift. Mitigation: explicit constants `AUTOPOST_ENABLED = False` enforced at the route level; PR review template asks "did this enable autopost?"
- **Complexity:** S-M.
- **Duration:** 0.5-1 day.
- **Tests:** assert the route never calls a publish endpoint of any third-party.
- **Launch impact:** Medium.
- **Rollback:** delete the route; operator drafts in their own tools.
- **Executor:** Claude-required for prompts; Codex-safe for plumbing.

---

### Sprint 4.2 — Sale attribution

- **Objective:** Connect a logged revenue event to the candidate, source, and channel that produced it.
- **Features:**
  - Revenue events gain `source_attribution` (free-text: subreddit URL, tweet URL, etc.) and `channel_tag`.
  - Optional Gumroad ping ingestion for the operator's account.
  - Daily attribution rollup view per source, per cluster.
- **Dependencies:** 4.0, 4.1.
- **Risks:** wrong attribution biases learning. Mitigation: operator can edit attribution after the fact; analytics treat events <24h old as provisional.
- **Complexity:** M.
- **Duration:** 1 day.
- **Tests:** create a sale, link to source, assert source_weight roll forward (using stub for 5.0).
- **Launch impact:** Medium.
- **Rollback:** revert the column additions (additive, safe).
- **Executor:** Codex-safe.

---

### Sprint 5.0 — Feedback learning loop

- **Objective:** Close the loop: revenue → source weights → rescoring.
- **Features:**
  - Nightly job updates `source_weights` based on attributed revenue per source over a 30-day window with exponential decay.
  - SIGNAL `calculate_score()` reads source weight and multiplies into `demand_velocity`.
  - Weight visualization on a new `/learning` page.
  - Manual override per source.
- **Dependencies:** 4.2.
- **Risks:** small data → unstable weights. Mitigation: smoothing + minimum-data threshold per source before weights leave 1.0.
- **Complexity:** M.
- **Duration:** 1-2 days.
- **Tests:** simulate revenue history; assert weight changes match expected formula.
- **Launch impact:** Medium.
- **Rollback:** force all weights back to 1.0 via setting; scoring degrades gracefully.
- **Executor:** Claude-required.

---

### Sprint 5.1 — Title and copy A/B (low-volume)

- **Objective:** Cheaply improve listings using a multi-armed bandit on titles.
- **Features:**
  - Each product has up to 3 title variants. Gumroad listing rotates which is current weekly. Sales attributed back per variant. Best variant promoted.
- **Dependencies:** 4.0, 4.2.
- **Risks:** insufficient volume to learn anything. Mitigation: ship behind a feature flag; default off until ≥ 5 products live.
- **Complexity:** M.
- **Duration:** 1 day.
- **Tests:** sim test of bandit decisions.
- **Launch impact:** Low until volume.
- **Rollback:** disable feature flag.
- **Executor:** Claude-required.

---

### Sprint 6.0 — Background queue + DLQ

- **Objective:** Long-running jobs (Ruflo runs, packaging, Gumroad uploads) move from synchronous routes to a real queue.
- **Features:**
  - Redis Streams or `arq`. Per-job idempotency key. DLQ visible at `/queues`.
  - Retry policy: exponential backoff, max 3, then DLQ.
- **Dependencies:** 4.x stable.
- **Risks:** queue divergence from DB state. Mitigation: jobs always update Postgres as the source of truth; queue is transport only.
- **Complexity:** L.
- **Duration:** 2 days.
- **Tests:** chaos test (kill worker mid-job) shows recovery.
- **Launch impact:** Medium.
- **Rollback:** synchronous routes remain available behind a flag for one sprint.
- **Executor:** Claude-required.

---

### Sprint 6.1 — Observability

- **Objective:** See spend, queue health, and revenue at a glance.
- **Features:**
  - Structured logging (`structlog`) shipped to Loki on Grafana free tier.
  - Prometheus metrics for: spend per agent per day, jobs per minute, DLQ size, listings/day, $/day.
  - Alert via Discord webhook on: spend > cap, DLQ > 0, zero listings in 24h, kill switch flipped.
- **Dependencies:** 6.0.
- **Risks:** alert fatigue. Mitigation: alerts default off; turn on one at a time.
- **Complexity:** M-L.
- **Duration:** 1-2 days.
- **Tests:** intentionally trip each alert.
- **Launch impact:** Low (operator-only).
- **Rollback:** disable exporters; logs return to stdout only.
- **Executor:** Codex-safe.

---

### Sprint 6.2 — Auto-publish gate (still operator-supervised)

- **Objective:** Allow Gumroad listings to auto-publish *if and only if* a strict allowlist of conditions is met. Still not real autonomy.
- **Conditions for auto-publish:** kill switch off; daily spend < cap; QA score ≥ threshold; URL well-formed; product has ≥ 1 file; opportunity cluster has ≥ 2 sources; operator has marked the product `autopublish_eligible`.
- **Dependencies:** 4.0, 5.0, 6.0.
- **Risks:** any single misconfiguration ships garbage publicly. Mitigation: this is the highest-stakes change in the project. Mandatory: a kill-switch test + a fresh end-to-end manual run on the day this ships, before enabling for any product.
- **Complexity:** L.
- **Duration:** 2 days.
- **Tests:** every gate exercised in CI.
- **Launch impact:** High.
- **Rollback:** flip `autopublish_eligible=false` for all products via SQL one-liner in `runbooks/rollback.md`.
- **Executor:** Claude-required + Human approval to enable for the first product.

---

### Sprint 7.0 — Etsy expansion (preparation)

- **Objective:** Multi-marketplace, before Etsy account verification finishes.
- **Features:** Etsy listing-draft adapter that mirrors the Gumroad shape. Manual paste path remains until API approval lands.
- **Dependencies:** 4.0, 6.2 stable.
- **Risks:** Etsy bans for AI content if disclosure missed. Mitigation: AI disclosure baked into the listing template.
- **Complexity:** L.
- **Duration:** 2 days (after account warm-up).
- **Tests:** mock Etsy API + golden listing.
- **Launch impact:** High once enabled.
- **Rollback:** disable adapter.
- **Executor:** Claude-required + Human (account work).

---

### Sprint 7.1 — Owned checkout (Stripe + landing pages)

- **Objective:** Escape platform dependency.
- **Features:** Stripe-checkout-backed product page per product (Astro on Cloudflare Pages or simple FastAPI route + Stripe Checkout).
- **Dependencies:** 7.0.
- **Risks:** payment compliance, refund handling. Mitigation: keep refunds manual.
- **Complexity:** L.
- **Duration:** 2-3 days.
- **Tests:** Stripe sandbox flows.
- **Launch impact:** High.
- **Rollback:** disable the routes; Gumroad/Etsy unaffected.
- **Executor:** Claude-required + Human (Stripe account, taxes).

---

### Sprint 7.5 — Print-on-Demand (POD) modality

- **Objective:** Add physical product revenue with zero inventory via Printify/Printful/Gelato API.
- **Why it fits HYDRA:** Designs are generatable (PNG/SVG via image gen). Fulfillment is fully automated. Etsy is already the primary POD storefront — no new marketplace onboarding. The operator's job remains approval-only.
- **Features:**
  - `ProductionFormat` type: `pod_design` — triggers a different generation pipeline (image prompt → PNG asset → product mockup).
  - Printify API adapter in Zone B: create product draft, upload design, set variants, get preview URL. Credentials stay in Zone B env vars, never in Zone A.
  - New `listings` platform values: `printify`, `printful`, `gelato`.
  - Operator approval gate: approve design + price before any publish call fires.
  - Revenue events tagged `marketplace=printify` etc. for attribution.
- **Dependencies:** 4.0 (Gumroad draft pattern), 7.0 (Etsy account live), image generation capability (see Sprint 8.0).
- **Risks:** Design quality. AI-generated designs need human review — the approval gate handles this. Printify TOS: no copyright infringement. Mitigation: no text reproducing brand names, no licensed characters.
- **Complexity:** L (API integration) + image gen pipeline (M).
- **Duration:** 3 days.
- **Tests:** Printify sandbox draft creation, mockup URL returned, listing row created.
- **Launch impact:** High — opens physical product revenue with zero warehouse overhead.
- **Rollback:** Disable the `pod_design` pipeline flag; existing digital products unaffected.
- **Executor:** Claude-required + Human (Printify account, first design approval).

---

### Sprint 8.0 — Revenue modality expansion (research + signal broadening)

- **Objective:** Systematically evaluate every legal automated-income modality and route qualifying signals into the right pipeline.
- **Why now:** Once digital downloads + POD are running, the highest-leverage next move is signal quality and modality fit — not more features.
- **Modalities to evaluate and route:**

  | Modality | Fit | Automation potential | Notes |
  |---|---|---|---|
  | Digital downloads (PDF, prompt pack, template) | ✓ Live | Full | Current primary |
  | Print-on-demand (apparel, prints, mugs) | ✓ Sprint 7.5 | Full | Printify/Printful |
  | Notion/Airtable templates | ✓ Live via Gumroad | Full | Already in prompt |
  | Stock assets (icons, illustrations, SVGs) | High | High | Creative Market, Envato |
  | Micro-SaaS tools (hosted utilities) | Medium | Medium | Requires infra + support |
  | Newsletter sponsorship (owned audience) | Medium | Low | Human relationship required |
  | Local business site template packs | High | High | "5-page plumber site + copy" sells on Gumroad/Etsy |
  | Course / video product | Low | Low | Too much human content required |
  | Affiliate content sites | Low | Low | SEO lag + Google risk |

- **Deliverable:** Updated `SIGNAL_DESIGN.md` with modality-aware scoring — candidates are routed to the right pipeline by production format, not just scored generically.
- **Dependencies:** 7.5 live, signal pipeline stable (Sprint 1.7+).
- **Complexity:** M (research + scoring update) — no new infrastructure.
- **Executor:** Claude-required (research + design). Human reviews modality rankings and approves additions.

---

## Part 3 — Critical path

The minimum sprints required for `detect → generate → launch → track → learn`:

```
1.4 (controlled LLM execution)  →  1.5 (in-process generation, multi-marketplace copy)
   →  1.6 (Alembic + listings table)  →  1.7 (Reddit + Celery scheduler)
   →  4.0 (Gumroad API draft)  →  4.2 (sale attribution)  →  5.0 (feedback loop)
```

That is **seven sprints** — same count, updated path. **Sprints 1.4–1.6 supersede the original 3.0/3.1/3.2** (Ruflo runner, QA gate, packager): the in-process agentic generation pipeline in Sprint 1.5 delivers equivalent capability without the Ruflo subprocess dependency. Sprints 3.0–3.2 are retained in the roadmap as optional Ruflo integration if the in-process pipeline proves insufficient for complex formats.

**Operator-minimal-touch target:** By Sprint 4.2, the operator's only required actions are:
1. Approve or reject a surfaced opportunity (10-second read of the pre-scored candidate)
2. Optionally add feedback notes before generation runs
3. Approve the final product for publish (review generated content + listing copy)

Everything else — signal collection, scoring, generation, listing copy, QA, distribution drafting, revenue tracking — runs without operator input.

Everything else is helpful but not blocking.

### Important but NOT blocking the first real loop

- 2.0 (Alembic) — pay down before column changes pile up; not blocking the first sale.
- 2.1 (Reddit + scheduler) — strengthens signal, but mock + HN already provides candidates.
- 2.2 (clustering + source weights table) — needed to make 5.0 meaningful, but 5.0 can ship using only attribution counts initially.
- 4.1 (distribution drafts) — operator can hand-write the first launch post.
- 6.0 / 6.1 (queue + observability) — improves resilience; not required for the first $9 sale.

### Implication

If a future contributor asks "what's the fastest path to first dollar with the agents online?", the answer is **1.3 → 3.0 → 3.1 → 3.2 → 4.0** with manual distribution and manual revenue logging. 4.2 + 5.0 close the *learning* loop afterward.

---

## Part 4 — Task classification

Classification is a contract: any task NOT clearly fitting Category A is Category B unless explicitly marked Human.

### Category A — Codex-safe

Boilerplate Codex can land without architectural drift, given a one-paragraph spec and the existing codebase as context.

- New SQLAlchemy model + migration + CRUD routes.
- New Jinja template, including form posts.
- New URL validation helper, slugify, formatter, exporter.
- New endpoint that wraps an existing helper or repo method.
- Adding a column to an existing model (additive).
- Pagination, filtering, sorting on existing list views.
- Read-only stats / dashboards that aggregate existing tables.
- Dockerfile or Compose changes (volumes, env vars, non-root user).
- Backup / restore scripts.
- Replacing print statements with structured logging.
- Adapter to a public REST/GraphQL API once the schema is documented.
- pytest harness, fixture seeding, CI workflow files.

### Category B — Claude-required

Tasks where one wrong assumption costs days.

- SIGNAL scoring formula changes.
- Cross-source clustering threshold and embedding choice.
- LLM prompt design (product outline, listing copy, QA critic).
- Choice of Ruflo subprocess interface and tool allowlist.
- Source-weight learning formula and decay.
- A/B / bandit policy.
- Boundary contract changes (anything that would let Zone A see credentials).
- Auto-publish gate conditions.
- Schema decisions that affect future migrations.
- Integration design for a new marketplace.
- Refactor that crosses Zone A / Zone B.

### Category C — Human-required

- Creating, verifying, or recovering any marketplace account.
- Pricing decisions on a live product.
- Posting in any community where moderators can ban accounts (Reddit, HN, Discord, Twitter, IndieHackers).
- Refunds and customer support replies.
- Final approval to flip `autopublish_eligible=true` on a product.
- Choosing which niche to pursue this week.
- Choosing whether to kill or pivot a product/niche.
- Reviewing AI-generated content before first publication in a new niche.
- Approving any spend > $10.

If a sprint has steps from multiple categories, decompose so each issue/PR belongs to exactly one.


---

## Part 5 — Operational continuity system

The point of this section: **anyone can pick up HYDRA mid-sprint without losing context.**

### Continuity artifacts

- `runbooks/SESSION_RECOVERY.md` is the first-read recovery procedure for any new model/session/operator.
- `runbooks/SPRINT_TEMPLATE.md` is the reusable sprint brief and handoff template.
- `logs/sprints/sprint_history.md` is the append-only sprint ledger.
- `logs/verification/verification_history.md` is the append-only human-readable verification ledger.
- `logs/runtime/runtime_events.jsonl` is the append-only runtime event ledger.
- `logs/revenue/revenue_events.jsonl` is the append-only revenue mirror; Postgres remains the source of truth.
- `scripts/status_snapshot.sh` prints the current branch, status, containers, roadmap recommendation, and sprint ledger tail.
- `scripts/preflight_check.sh` validates Docker, Compose services, Postgres, Redis, and FastAPI health.
- `scripts/validate_env.sh` checks required local environment variables without failing hard on non-critical gaps.
- `scripts/sprint_closeout.sh` appends a timestamped closeout snapshot to the sprint ledger.

Continuity rule: append, do not rewrite. Corrections get a new timestamped entry.

### Sprint handoff protocol (mandatory)

Every sprint ends with a commit on `main` whose tree contains:

1. `runbooks/sprint_<id>_handoff.md` — produced from `runbooks/SPRINT_TEMPLATE.md`.
2. Updated `runbooks/launch_day.md` if any operator-facing flow changed.
3. Updated `runbooks/ROADMAP.md` "Last updated" line and any sprint metadata that drifted.
4. A passing run of the relevant `scripts/verify_*.sh` script(s).
5. A `runbooks/known_issues.md` line per non-blocking issue discovered.
6. A `runbooks/rollback.md` entry naming the exact revert procedure for any irreversible change in the sprint.

If any one of these is missing, the sprint is not done — the next agent is allowed (and expected) to refuse to start the next sprint until the handoff is complete.

### Required sprint artifacts

| Artifact | Purpose | Owner |
|---|---|---|
| `runbooks/sprint_<id>_handoff.md` | Inspection summary, files changed, commands run, verification results, known issues, recommended next sprint | Sprint executor |
| `runbooks/known_issues.md` | Append-only list of non-blocking issues with file:line references | Sprint executor |
| `runbooks/rollback.md` | Per-feature revert procedures | Sprint executor (irreversible-change sprints) |
| `runbooks/commands_run.md` | Append-only log of significant shell commands per sprint | Sprint executor |
| `runbooks/verification_results.md` | Append-only summary of what was verified, with timestamps | Sprint executor |
| `scripts/verify_<feature>.sh` | Reproducible end-to-end verification | Sprint executor |
| `runbooks/launch_day.md` | The operator's checklist for tonight's launch | Sprint executor |

### Git discipline

- **Branch model:** trunk-based. Default branch is `main`. Sprint work happens on `sprint/<id>-<slug>` branches, merged via fast-forward or squash.
- **Commit naming:** `sprint <id>: <imperative summary>` (e.g. `sprint 1.3: add LLM client with daily budget`). Sub-commits within a sprint can use `<id>:` prefix.
- **PR description template** lives at `.github/pull_request_template.md` and includes:
  - Sprint id and link to the sprint handoff doc.
  - "Boundary review" checkbox: did this PR touch the Zone A / Zone B boundary?
  - "Spend review" checkbox: does this PR add a path that can spend money?
  - "Rollback procedure" line.
- **Tags:** every sprint completion tagged `sprint-<id>`. Acts as a known-good rollback target.
- **Rollback process:** `git checkout sprint-<previous_id>` recovers a known-good state. Database rollback uses the most recent backup + `runbooks/rollback.md`.

### Runbook standards

Every runbook starts with:

```
# <Title>
**Sprint:** <id>     **Last updated:** YYYY-MM-DD
**Owner:** Operator (jb)
**Purpose:** <one sentence>
```

And uses the sections that apply: `What it does`, `When to use`, `Inputs`, `Steps`, `Expected output`, `Failure modes`, `Rollback`, `Related runbooks`.

### Session recovery process

A new agent (Codex / Claude / ChatGPT) inheriting HYDRA reads, in order:

1. `runbooks/ROADMAP.md` (this file) — full strategic context.
2. `runbooks/sprint_<latest>_handoff.md` — most recent state.
3. `runbooks/known_issues.md` — open hazards.
4. `runbooks/rollback.md` — what is reversible and how.
5. `git log --oneline -20` — recent history.
6. `docker compose ps && curl localhost:8000/health` — confirm the stack actually runs.
7. The verification script for the most recent sprint.

The new agent then writes one paragraph in the chat: "I read the handoff and verified state X, Y, Z. The next sprint is N because of the critical-path table." Only then does work begin. **No agent starts coding before producing this paragraph.**


---

## Part 6 — Risk register

Probability and severity scored Low / Medium / High. Mitigations are mandatory; review this register at the start of every sprint.

| # | Risk | P | S | Mitigation |
|---|---|---|---|---|
| 1 | **API spend runaway** — buggy retry loop burns the budget overnight | M | H | Hard daily cap in `app/llm.py` checked *before* the call. Per-call cap. Circuit breaker on consecutive failures. Discord alert when 80% of cap reached. |
| 2 | **Marketplace ban** — Etsy/Gumroad flag the shop for AI/spam patterns | M | H | Mandatory AI disclosure. ≤ 3 listings/day max. Manual publish. Diversify across marketplaces by month 3. |
| 3 | **Bad signal quality** — noisy candidates dominate scoring | H | M | Cross-source confirmation gate (≥ 2 sources). Volume floor. Saturation probe. Weekly operator audit of top 20 candidates. |
| 4 | **Duplicate products** — race or replay creates two listings of the same thing | M | M | Idempotency keys on `Product.opportunity_id` (already enforced) and `Product.gumroad_draft_id`. Listing-creation route must look up by idempotency key before POSTing. |
| 5 | **AI slop ships publicly** — generator output reaches buyers | M | H | QA gate (3.1) blocks transition to `generated`. Operator must publish manually until 6.2. Sample 1 in 5 even after auto-publish enabled. |
| 6 | **Launch paralysis** — endless polishing, no live products | H | H | Definition of done is binary: does a buyer URL exist? Sprint deadlines are hard. Operator commits to ship 1 product/week minimum during 1.x-3.x. |
| 7 | **Infra drift** — VPS state diverges from repo | M | M | Compose-only deployment. `scripts/bootstrap_vps.sh` is the truth. No SSH-side edits without committing them back. |
| 8 | **Context loss** — agent or operator loses thread between sessions | H | M | Sprint handoff protocol (Part 5) is the primary defense. Every sprint produces a handoff doc and an updated roadmap line. |
| 9 | **Autonomous posting drift** — someone re-enables a third-party auto-post path | L | H | `AUTOPOST_ENABLED = False` enforced at module level. PR template requires explicit checkbox. CI grep for `AUTOPOST_ENABLED = True`. |
| 10 | **Copyright / IP issues** — generated cover/content too close to existing IP | M | H | Denylist of trademarked terms in `app/policy/denylist.txt`. Cover-image source tracked in metadata. Manual review of any image in a new niche. |
| 11 | **Schema drift** — `create_all` masks broken columns, surfaces in prod | M | M | Sprint 2.0 baselines Alembic; after that, schema changes only via migrations. CI lint rejects model changes without a paired migration. |
| 12 | **Single-machine fragility** — VPS dies, all state lost | M | H | Nightly `pg_dump` to host disk + weekly off-host copy. Restore tested monthly (calendar reminder). |
| 13 | **Operator burnout** — solo founder fatigue mid-cycle | H | H | Time-boxed sprints. ≤ 25 hrs/week steady state after Sprint 1.3. Schedule explicit "off" days. |
| 14 | **Ruflo upstream churn** — new release breaks subprocess bridge | M | M | Pin a Ruflo tag. Vendor a fork. CI runs the bridge test against the pinned version daily. |
| 15 | **Overengineering / AGI drift** — over-scoping each sprint | H | M | This roadmap is the contract. Any "while we're here" addition costs a sprint metadata entry. |
| 16 | **Credential leak** — Gumroad/Anthropic key in repo | L | H | `.env` in `.gitignore`; pre-commit hook scans for known key patterns; secrets only on VPS. |
| 17 | **Operator-as-single-point-of-failure** — only jb knows the system | M | H | This roadmap + handoff docs are the recovery plan. README written so a sibling/partner could resume. |
| 18 | **Trade or money-handling drift** — agent ever placing orders or moving funds | L | H | Hard rule: HYDRA never executes financial transactions besides Stripe-backed product purchases initiated by buyers. Document in guardrails (Part 8). |

---

## Part 7 — First real revenue plan

Path from current state (end of Sprint 1.2) to **first paid sale**, in steps that fit with current code and don't require shipping any new sprint first. The goal: **first $9 sale within 7 days of today**, with HYDRA as the factory and operator as the publisher.

### Step 0 — Pre-flight (today, ≤ 30 min)

- Confirm `docker compose up` clean. `curl /health` 200.
- Confirm Anthropic key + OpenAI key present in `.env` (used in Sprint 1.3, but useful even now for offline outline drafts via Claude Code locally).
- Confirm Gumroad account exists; if not, create it. Add payout method.
- Confirm operator owns at least one distribution channel (Twitter/X, blog, niche subreddit account with karma, niche Discord membership) where buyers actually live.

### Step 1 — Real signal (today, 30 min)

- Click "Collect HackerNews AI Signals" on `/opportunities`.
- Run mock SIGNAL scan once for additional ideas.
- Sort by score, scan top 15 candidates manually. The operator picks **one** that fits all of:
  - Topic is fresh (in HN front page or recent Reddit thread within last 72h).
  - Operator has insider familiarity (DevOps / SRE / homelab / AI tooling).
  - Production format is `cheat sheet PDF` or `prompt pack` (fastest to ship).

### Step 2 — Approve + edit prefilled draft (today, 15 min)

- Click Approve on the chosen candidate. Lands on prefilled `/products/<id>/edit`.
- Operator edits title to be specific and benefit-led. Sets price ($9 to start).
- Saves notes with the deliverable structure they actually want.

### Step 3 — Generate content with Ruflo / Claude Code (today, 2-3 hrs)

- Copy the Ruflo Product Prompt from the Opportunities page into Ruflo or Claude Code locally.
- Paste returned outline into Add Artifact (`outline` type).
- Iterate sections in Ruflo. Paste each into Add Artifact (`product_content`).
- Run a critique pass with a different LLM family. Paste into Add Artifact (`qa_review`).
- This is manual today; Sprint 3.0 + 3.1 automate it.

### Step 4 — Package locally (today, 30 min)

- Click "Export Artifacts to /exports". Get Markdown files on host.
- Convert Markdown → PDF with Pandoc: `pandoc 002_product_content_*.md -o package/pack.pdf`.
- Build a cover image in Canva (no AI gen tonight; template).
- Zip: `cd exports/product_<id> && zip -r ../my-pack.zip *`.
- Add a `product_files` row pointing to the ZIP.

### Step 5 — Gumroad listing (today, 30 min)

- Manually create the Gumroad product. Paste listing copy from the listing prompt + critic output. Upload ZIP. Set price.
- Mark the listing live.
- In HYDRA: set `Product.status="live"` and `Product.gumroad_url=<URL>`. The launch dashboard's "Missing URL" count should drop.

### Step 6 — Distribution (today, 1 hr)

- One post in the *exact community* the candidate's evidence pointed to. Operator posts manually, answering a real question with the link as a postscript. **Not on autopost.**
- One thread on operator's own X / blog if applicable.
- That is it for tonight. No multi-channel blast.

### Step 7 — Watch (next 48-72 hrs)

- Refresh `/launch` daily. When the first sale lands:
  - Add a manual `RevenueEvent` with the URL of the post that drove it (free-text in notes).
  - Take a screenshot. Save to `runbooks/wins/<date>-<product-slug>.png`.
- Even one sale validates the entire pipeline. The next sprint can start.

### What this proves

- The Zone A / Zone B boundary works under real conditions.
- The prefill, artifact, file tracking, export, and launch dashboard are sufficient for one product end-to-end.
- A real revenue event flows back through HYDRA's ledger, ready to feed Sprint 5.0 once attribution lands.

### What it doesn't prove (and that's OK)

- That HYDRA can run unattended.
- That the system scales beyond one product per week.
- That the chosen niche is the right long-term niche.

Those are 5.0 + 6.x problems.


---

## Part 8 — Long-term architecture guardrails

**HYDRA must never become:**

- An overbuilt AGI fantasy. Agents are bounded, observable, and replaceable.
- An autonomous spam machine. Every external posting action requires HITL until further notice.
- An uncontrolled social bot. No third-party platform credentials inside Zone A.
- A high-burn infrastructure system. Single VPS until $1k MRR, full stop.
- A microservice maze. New services require explicit justification in the sprint that adds them.
- A vendor-lock cage. Every AI provider is replaceable inside `app/llm.py`.

### Architectural principles

1. **Postgres is the source of truth.** Redis, AgentDB, vector caches are derived state that can be rebuilt.
2. **Idempotency by default.** Every job has a deterministic key; re-runs are safe.
3. **Boundary-first.** Zone A (creative) and Zone B (state/money) are separated by a queue or HTTP boundary, never a function call across credentials.
4. **Boring tech wins.** FastAPI + Postgres + Redis + Docker Compose. New tech enters only when an existing problem cannot be solved with the current stack.
5. **Every external action is observable.** No silent retries; every LLM call, every marketplace call is logged with cost.
6. **HITL by default.** New automation is opt-in per product/route; defaults stay manual until proven safe.
7. **Append-only audit trail** for approvals and revenue. Edits create new rows, not mutations.
8. **Reversible deployment.** Every sprint produces a `git tag` + a `pg_dump` that allow rollback in < 10 minutes.

### Operational philosophy

- Ship one working thing per sprint. Skip rather than half-build.
- Verification scripts exist before features ship. No feature is "done" without a `verify_*.sh` script.
- Documentation is part of the deliverable, not a follow-up.
- Operator hours are the scarcest resource. Optimize for operator hours, not infrastructure cost.
- Refuse to start the next sprint without the previous handoff.

### Scaling philosophy

- Vertical first (bigger VPS) before horizontal (multiple services).
- Managed databases (Neon/Supabase) only after the local DB is the actual bottleneck.
- Kubernetes is forbidden until $5k MRR and at least 5 deployed services.
- Custom or fine-tuned models are forbidden until the cost of a hosted call > the cost of fine-tuning, sustained for 30 days.

### Automation philosophy

- The first time a task runs, a human runs it.
- The second time, a script runs it with a human watching.
- The third time, the script runs and the human reads the result.
- The Nth time, the script runs and an alert fires only on anomaly.
- Posting in any community where moderators can ban is **never** automated. There is no Nth time.
- Money movement is **never** automated. Buyer-initiated checkouts only.


---

## Part 9 — Execution priorities

### Immediate next sprint recommendation

**Sprint 1.3.** Specifically: ship the `app/llm.py` budget-guarded client and replace `build_default_product_fields()` notes block with a Haiku-backed call. The non-root Dockerfile and the `llm_calls` table land alongside.

Why 1.3 first instead of 2.0 (Alembic):

- 1.3 unlocks every subsequent automation step. 2.0 only protects future schema changes.
- Schema additions in 2.x are still safe under `create_all()` for one more sprint.
- The operator already asked for LLM-prefill explicitly.

### Highest-ROI implementation right now

A working `app/llm.py` with daily budget enforcement. Every future agent (Trend Scout v2, QA, classifier, prefill, listing copy) routes through it. Get this right once, never reinvent.

### Biggest waste of time right now

- Building a dashboard refresh / charting layer before there is meaningful data to chart.
- Replacing HTTP basic auth before going public — pure local UX work that doesn't change a buyer's experience.
- Generic prompt engineering against the entire Ruflo agent surface — ROI compounds in *vertical* prompts (specific niche, specific format), not in framework-level cleverness.
- Migrating to async FastAPI without a real concurrency need.
- Picking a "cooler" frontend (React, Next, htmx-everywhere). HTMX + Jinja is fine through Sprint 6.x.

### Biggest hidden opportunity

The `evidence` field on each `OpportunityCandidate`. It already contains the buyer's own words from public sources. That is the most expensive data in marketing — and it is sitting in the database waiting to be re-used as listing-copy raw material, search-keyword input, and audience-targeting hints. Sprint 3.x prompt design should lift directly from `evidence`.

### Biggest hidden danger

Quietly slipping marketplace credentials into a Zone A prompt because "Ruflo would do a better job if it could just see the listing." This is the failure mode that ends the project. The boundary law in the README and PR template exists for this exact temptation.

---

## Appendix A — Sprint dependency graph

```
1.2 (DONE)
  └─ 1.3 (LLM client + budget + non-root Dockerfile)
       ├─ 2.0 (Alembic + backups)
       │     └─ 2.1 (Reddit + scheduler)
       │           └─ 2.2 (clustering + source weights table)
       │                 └─ 5.0 (feedback learning loop)
       │                       └─ 5.1 (title A/B)
       └─ 3.0 (Ruflo runner)
             └─ 3.1 (QA gate)
                   └─ 3.2 (Packager)
                         └─ 4.0 (Gumroad draft)
                               ├─ 4.1 (distribution drafts)
                               ├─ 4.2 (sale attribution) ──► 5.0
                               └─ 6.0 (queue + DLQ)
                                     └─ 6.1 (observability)
                                           └─ 6.2 (auto-publish gate) ──► 7.0 (Etsy)
                                                                          └─ 7.1 (Stripe checkout)
```

## Appendix B — Glossary

- **Zone A:** creative/generative swarm. Ruflo, Claude Code, Codex. Produces artifacts only.
- **Zone B:** deterministic state layer. FastAPI + Postgres + Redis. Owns approvals, money, URLs.
- **Boundary law:** the rules separating Zone A from Zone B. Codified in `runbooks/ruflo_boundary.md`.
- **Approval:** a row in `approvals` table marking an explicit operator decision. Append-only.
- **Cluster:** a group of `OpportunityCandidate` rows that the system thinks describe the same opportunity.
- **Source weight:** multiplier applied to `demand_velocity` based on a source's historical revenue contribution.
- **HITL:** Human-in-the-loop. A point in a workflow where an operator must explicitly approve.
- **Kill switch:** `system_flag('hydra:kill','true')`. When on, all gated actions refuse with HTTP 423.
- **DLQ:** dead-letter queue. Where jobs go after exceeding the retry budget.

## Appendix C — How to use this roadmap

- **Operator (jb):** read Part 1 and Part 9 weekly. Read Part 7 before any launch attempt. Use Part 6 as a sanity check before any sprint.
- **Claude (architecture / prompt design):** read the full doc when starting a session. Update Part 2 metadata as sprints ship. Refuse to begin a Category B task without explicitly identifying the affected sprint.
- **Codex (implementation):** read Part 4 and the relevant Part 2 sprint entry. Refuse to start coding if a sprint is ambiguous; ask for the spec instead. Always finish with the handoff artifacts in Part 5.
- **ChatGPT or any other agent:** read Part 5 first; produce the recovery paragraph before doing anything else.


---

## Appendix D — Sprint 1.3 actual outcome (logged 2026-05-08)

Sprint 1.3 was pivoted from the originally-planned "Controlled LLM Execution Layer" to **Launch Learning v1** with operator approval. The original LLM-execution-layer scope is reassigned to **Sprint 1.4** below. The roadmap dependency graph in Appendix A is unchanged in shape; only the labels move down by one.

Reasoning: after product 35 launched on real signal, the binding constraint flipped from "we have no LLM client" to "we have no attribution data on the one real launch." Sprint 1.3 closed the latter; Sprint 1.4 will close the former.

Sprint 1.3 shipped: attribution columns + idempotent `ALTER` migrations, distribution-post publish flow, sale attribution form, channel rollup on `/launch`, "Live without distribution" metric, title prefill cleanup, keyword-based HN classifier, auto-registration of `product_files` on export, `.gitignore`. Verified PASS in `scripts/verify_sprint13.sh` (13/13). See `runbooks/sprint_1.3_handoff.md`.

---

## Appendix E — Sprint 1.4 plan (paste-ready spec)

> **For the next session:** if you are picking up cold, read `runbooks/CLAUDE_RESUME_PROMPT.md`, run the inspection block, produce the strategic evaluation, then implement this spec. Reject any of the listed scope creep.

### Sprint 1.4 — Controlled LLM Execution Layer

- **Objective:** Introduce a single, budget-guarded LLM client and use it to upgrade two existing surfaces (HN classifier, approval prefill notes). No autonomous swarm. No new collectors. No publishing.
- **Why now:** Sprint 1.3 made attribution data available. The next compounding lever is turning the `evidence` field — already paid for — into better classification and prefill, which the operator can edit in seconds instead of minutes.

#### Features (do all)

1. **`app/llm.py` — single client, two providers, hard guards.**
   - Methods: `complete(prompt, *, model, max_tokens, agent="generic", purpose="...")` — returns the completion string.
   - Providers: Anthropic (Claude Haiku) primary; OpenAI (`gpt-4o-mini`) fallback. Both keys via env. Fail closed if neither is set.
   - Hard daily cap: read `daily_budget_usd` system flag. If today's `llm_calls.cost_usd` sum + estimated cost of this call > cap, raise `BudgetExceeded` BEFORE the call.
   - Per-call cap: max $0.20 estimated cost. Reject larger.
   - Kill-switch: `assert_system_can_act("llm_call")` before any provider call.
   - Timeout: 20 s per call. Single retry on transient errors (5xx / network), no retry on 4xx.
   - Logs: every call writes a `llm_calls` row (id, model, agent, purpose, prompt_tokens, completion_tokens, cost_usd, duration_ms, status, occurred_at).
2. **`llm_calls` table.** New SQLAlchemy model. Auto-created at startup like the others.
3. **Settings page extension.** Show today's spend vs cap, count of calls, last-call timestamp.
4. **Replace `_hn_classify` with an LLM classifier.**
   - Keep the existing rules-based router as the deterministic fallback for budget-exceeded / kill-switch / API-failure paths.
   - Prompt: "Given this HN story title and snippet, classify the buyer audience and best digital-product format. Return strict JSON with `vertical` and `production_format`."
   - Cost ceiling per call: $0.0005 (Haiku at ~200 tokens).
5. **Replace the deterministic notes block in `build_default_product_fields()` with an LLM-generated structured notes block.**
   - Prompt: includes the candidate's `evidence`, `vertical`, `production_format`, and `topic`. Returns: 8-line outline + buyer pain summary + suggested deliverable structure.
   - Cost ceiling per call: $0.001.
   - Falls back to the existing deterministic block on any failure.
6. **Verification script** `scripts/verify_sprint14.sh`:
   - Asserts `llm_calls` table exists with expected columns.
   - Asserts a real call lands a row with `cost_usd > 0`.
   - Asserts kill switch ON blocks the call (HTTP error or fallback path triggered).
   - Asserts setting `daily_budget_usd=0` triggers the `BudgetExceeded` fallback path.
   - Asserts the LLM classifier returns valid JSON for at least one fixture title.

#### Dependencies

- 1.3 (attribution) — DONE.
- Anthropic and/or OpenAI API key in `.env`.

#### Risks

- **Spend leak.** Mitigated by pre-call budget check + per-call cap + circuit breaker on consecutive failures.
- **Hallucinated classification.** Mitigated by the rules-based fallback remaining the source of truth on parse failures.
- **Schema drift.** New table only (additive); safe under `create_all`.

#### Complexity / duration

- M-L. ~1–1.5 focused days.

#### Acceptance

- Budget cap enforced before the call, not after.
- Kill switch blocks LLM calls cleanly.
- Both upgraded surfaces (HN classifier, prefill notes) fall back deterministically on any failure.
- `verify_sprint14.sh` PASS.

#### Do NOT add in 1.4

- A real Reddit / Product Hunt collector.
- Automated publishing or distribution.
- Streaming or async LLM calls.
- A vector store or embeddings (defer to 2.2 with clustering).
- Replacement of basic auth.
- Any UI prettification beyond the Settings spend readout.
- Background scheduling.

#### Files expected to change

- `app/llm.py` (new), `app/db.py` (new model + import), `app/main.py` (replace classifier + prefill calls; budget readout in `/settings`), `app/templates/settings.html`, `requirements.txt` (add `anthropic` and `openai` SDKs), `.env.example` (add `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`), `scripts/verify_sprint14.sh` (new), runbooks updated per template.
### Sprint 1.7 — Marketplace Intelligence v1

**Status:** IN PROGRESS (2026-05-10)
**Preceded by:** Sprint 1.5.1 (LLM Observability + UX Polish)
**Followed by:** Sprint 4.0 (Gumroad publishing automation)

**Strategic pivot rationale:** Original Sprint 1.7 (Reddit collector + Celery scheduler) was
deprioritized in favor of Marketplace Intelligence v1. Reddit signals are demand-adjacent;
Etsy/marketplace signals are purchase-intent. Market intelligence feeds the opportunity→product
loop with patterns grounded in observed buyer behavior, not forum discussion.

**What this sprint adds:**
- `market_research_runs` — one row per research session (manual or CSV)
- `market_research_items` — one observed listing/product per row
- `market_patterns` — LLM-extracted winning patterns from a run
- Routes: list, new, create, detail, import-csv, analyze, generate-opportunities, delete
- Templates: `market_research_list.html`, `market_research_detail.html`
- Nav link: "Market Research" added to base.html
- Verify: `scripts/verify_sprint17.sh`
- Sample data: `scripts/sample_research.csv`
- Codex brief: `runbooks/sprint_1.7_codex_brief.md`

**Operator flow:**
1. Create research run
2. Import CSV of marketplace observations (manual research or tool export)
3. Click "Analyze Patterns" → LLM extracts title structures, pricing ranges, pain points, etc.
4. Review extracted patterns
5. Click "Generate Opportunities" → LLM creates original product ideas from patterns
6. Approve candidates in /opportunities UI (human gate — unchanged)
7. Approved candidates flow into existing generation pipeline

**Human approval gates (unchanged):**
- Selecting which opportunity to approve
- Final product approval before publishing
- Any action touching external accounts or public content

**Do NOT add in 1.7:**
- Etsy API OAuth or publishing
- Automated marketplace scraping
- Celery/Redis scheduler
- Image generation
- Auto-publishing
- Printify/POD integration
- Embeddings or vector search

**Acceptance criteria:**
- `bash scripts/verify_sprint17.sh` exits 0
- `LIVE=1 bash scripts/verify_sprint17.sh` exits 0
- `alembic upgrade head` from 0002 applies 0003 cleanly
- `alembic downgrade 0002` drops all 3 new tables cleanly
- CSV import → analyze → generate-opportunities creates candidates visible in /opportunities
- No candidate auto-advances past pending_review without operator action
- Background scheduling.

#### Files expected to change
