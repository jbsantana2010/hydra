# Sprint 1.5 Handoff — In-Process Agentic Generation (Multi-Marketplace)

**Sprint:** 1.5
**Started:** 2026-05-09
**Completed:** 2026-05-09
**Executor:** Claude (Chief Architect)
**Boundary touched:** no — Zone A/Ruflo remains artifact-only; no marketplace credentials added
**Spend touched:** yes — five new LLM-backed generation routes, all budget-gated

## 1. Strategic Context

Sprint 1.5 implements the first step of agentic product generation, directly addressing the
binding bottleneck: 3-4 hours of manual operator work per product. After this sprint, a
complete product (outline → content → listing copy → QA → distribution posts) can be
generated in under 15 minutes of operator review time, with all LLM spend logged and capped.

Multi-marketplace scope is baked in from day one. Listing copy is generated simultaneously for:
- **Gumroad** — conversational, benefit-led descriptions
- **Etsy** — SEO-first title (≤140 chars), exactly 13 tags (≤20 chars each), keyword-rich description
- **Sellfy** — punchy conversion-focused copy
- **Payhip** — friendly, benefit-first copy

This matches the operator mandate: "evolve toward an Etsy/Gumroad digital product operating
system... make money like its life depended on it."

## 2. Files Changed

### Modified
- `app/llm.py` — added `reverse_providers: bool = False` to `call_llm_json()`; updated
  `_providers()` to accept `reverse` flag and return reversed list when True. QA uses this
  to critique with the alternate model family.
- `app/main.py` — added `import json`; added `_latest_artifact()`, `_artifact_context()`,
  `_generation_error()` helpers; five new generation routes; updated `edit_product` to pass
  `generation_status` dict to the template.
- `app/templates/product_edit.html` — added "Generate" section with five step panels showing
  prerequisite status, done/not-done state, and action buttons.
- `runbooks/known_issues.md` — Sprint 1.5 items appended.
- `runbooks/verification_results.md` — Sprint 1.5 row appended.
- `runbooks/commands_run.md` — Sprint 1.5 commands appended.

### Created
- `scripts/verify_sprint15.sh` — Sprint 1.5 verification.
- `runbooks/sprint_1.5_handoff.md` — this document.

## 3. New Routes

| Route | Prerequisite | Purpose | Max cost/call |
|---|---|---|---|
| `POST /products/{id}/generate/outline` | none | Multi-marketplace product outline | $0.003 |
| `POST /products/{id}/generate/content` | outline artifact | Full product content for all sections | $0.012 |
| `POST /products/{id}/generate/listing` | product_content artifact | Listing copy for Gumroad + Etsy + Sellfy + Payhip | $0.006 |
| `POST /products/{id}/generate/qa` | product_content artifact | Adversarial QA using alternate model | $0.006 |
| `POST /products/{id}/generate/distribution` | listing_copy artifact | Platform-native posts for Reddit/X/HN/IH | $0.006 |

Total cost per complete product generation run: ~$0.033. At $3/day budget, this supports ~90 complete runs per day.

## 4. Behavior

- All five routes call `call_llm_json()` — kill switch, daily budget, and per-call cap all apply.
- On `LlmBlocked` or `LlmFailed`: routes return JSON `{"status": "blocked"|"failed", "action": "...", "message": "..."}` — no crash, no 500.
- On prerequisite not met: routes return JSON `{"status": "missing_prereq", ...}` — no LLM call made.
- On success: routes redirect 303 to `/products/{id}/edit`.
- QA route uses `reverse_providers=True` — critique uses the alternate model family (if Anthropic generated content, OpenAI reviews, and vice versa). Falls back gracefully if only one provider is configured.
- Every generation artifact is saved with `source="hydra-llm:<step>"` for provenance tracking.

## 5. Verification Results

`scripts/verify_sprint15.sh` — see `runbooks/verification_results.md`.

## 6. Known Issues

See `runbooks/known_issues.md` for Sprint 1.5 items.

## 7. Rollback

Remove the five generation routes from `app/main.py` (the `# Sprint 1.5` block at the bottom).
Remove `generation_status` from `edit_product`. Remove the Generate section from `product_edit.html`.
Revert `llm.py` `reverse_providers` additions. No schema changes; no migration needed.

## 8. Boundary Review

- [x] No Ruflo credentials added.
- [x] No marketplace credentials added or passed to LLM prompts.
- [x] No revenue mutation by LLM.
- [x] No autonomous publishing or posting.
- [x] No LLM calls outside `app/llm.py`.
- [x] Zone A boundary intact — operator still clicks each generation step.

## 9. Recommended Next Sprint

**Sprint 1.6** — Alembic baseline + pg_dump backups + multi-platform `listings` table.

This is Codex-safe and unblocks Sprint 4.0 (Gumroad API draft creation) by giving us proper
schema management before the first marketplace credential lands. Full spec in
`runbooks/sprint_1.6_codex_brief.md`.
