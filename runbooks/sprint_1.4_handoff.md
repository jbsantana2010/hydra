# Sprint 1.4 Handoff — Controlled LLM Execution Layer

**Sprint:** 1.4
**Started:** 2026-05-09
**Completed:** 2026-05-09
**Executor:** Codex
**Boundary touched:** no — Zone A/Ruflo remains artifact-only
**Spend touched:** yes — guarded LLM client added, but verification ran with no API keys and spent $0.00

## 1. Spec Read

Authoritative spec was read from `runbooks/ROADMAP.md` Appendix E: "Sprint 1.4 — Controlled LLM Execution Layer." It required one budget-guarded LLM client, used only for HN classification and product draft notes/prefill, with deterministic fallback behavior.

## 2. Files Changed

### Modified
- `app/db.py` — added `LlmCall` model/table.
- `app/main.py` — settings readout, LLM-backed HN classification with rules fallback, LLM-backed product notes with deterministic fallback.
- `app/templates/settings.html` — today spend vs cap and recent calls table.
- `app/requirements.txt` — added Anthropic/OpenAI SDK pins.
- `.env.example` — added LLM provider env placeholders and per-call cap.
- `docker-compose.yml` — passes LLM env vars into the app container.
- `runbooks/known_issues.md` — Sprint 1.4 caveats.
- `runbooks/verification_results.md` — Sprint 1.4 verification table.
- `runbooks/commands_run.md` — Sprint 1.4 command log.
- `runbooks/rollback.md` — Sprint 1.4 rollback section.
- `logs/sprints/sprint_history.md` — Sprint 1.4 closeout entry.

### Created
- `app/llm.py` — single guarded LLM client.
- `scripts/verify_sprint14.sh` — Sprint 1.4 verification.
- `runbooks/sprint_1.4_handoff.md` — this handoff.

## 3. Schema Changes

New additive table via `Base.metadata.create_all()`:

```sql
llm_calls (
  id SERIAL PRIMARY KEY,
  provider TEXT,
  model TEXT,
  purpose TEXT,
  prompt_tokens INTEGER DEFAULT 0,
  completion_tokens INTEGER DEFAULT 0,
  cost_usd NUMERIC DEFAULT 0,
  duration_ms INTEGER,
  status TEXT,
  error TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

No existing table columns were changed.

## 4. Behavior

- All LLM calls go through `app/llm.py`.
- `assert_system_can_act("llm_call")` runs before provider calls.
- Daily budget is read from `daily_budget_usd`.
- Per-call cap is `HYDRA_LLM_PER_CALL_CAP_USD`, default `$0.20`.
- HN classifier attempts LLM JSON, then falls back to Sprint 1.3 keyword rules.
- Approval prefill attempts LLM structured notes, then falls back to deterministic notes.
- Missing keys, budget blocks, kill switch, provider failure, timeout, invalid JSON, and bad responses all preserve fallback behavior.

## 5. Verification Results

`scripts/verify_sprint14.sh` — PASS.

Verified:

- App imports.
- `llm_calls` table and expected columns.
- `/health`.
- Settings page LLM spend and recent calls.
- Kill switch blocks `llm_call`.
- `daily_budget_usd=0` blocks `llm_call`.
- Blocked attempts log rows.
- HN fallback classifier returns valid candidates.
- HN collection works without API keys.
- Product approval still creates draft product with notes.
- Products, Revenue, and Launch pages render.

Real provider call was skipped because no API keys were configured. The script will run it automatically when keys exist.

## 6. Known Issues

- Cost/token accounting is conservative when providers do not return usage metadata.
- API-key-free verification proves fallback/guard behavior; real provider smoke requires `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`.
- Existing pre-Sprint 1.4 issues remain in `runbooks/known_issues.md`.

## 7. Rollback

Use the Sprint 1.4 section in `runbooks/rollback.md`.

The `llm_calls` table is append-only and safe to leave in place during code rollback.

## 8. Boundary Review

- [x] No Ruflo credentials added.
- [x] No marketplace publishing added.
- [x] No revenue mutation by LLM.
- [x] No autonomous behavior added.
- [x] No LLM calls outside `app/llm.py`.

## 9. Recommended Next Sprint

Choose based on operator priority:

- More launch experiments if the immediate goal is buyer feedback.
- Reddit collector if the immediate goal is broader real signal intake.
- Product packaging improvements if the immediate goal is faster delivery quality.
- Attribution/source-weight learning if there are enough sales/events to justify learning.

My recommendation: product packaging improvements unless the operator has a clear Reddit niche list ready.
