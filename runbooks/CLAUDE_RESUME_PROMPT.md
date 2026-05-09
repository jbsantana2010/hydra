# Claude Resume Prompt — copy from inside the fence

Use this when Claude returns. Paste only the contents between the `---PROMPT START---` / `---PROMPT END---` markers.

---PROMPT START---

You are Claude resuming work as Chief Architect and Lead Engineer for HYDRA.

Working folder: `/home/jb/dev/hydra`.

**Read-first, code-later.** Do NOT modify any file or run any non-read-only command until you have produced the strategic evaluation at the bottom of this prompt. If you cannot produce that evaluation truthfully, say so and stop.

## What changed since your last session

HYDRA crossed a real threshold while you were away:

- **First end-to-end operational launch loop ran on real signal.** HackerNews collector → operator-approved opportunity (`SafeSandbox – infinite undo for AI coding agents`) → derivative legal product (`AI Coding Agent Safety Pack`, product id 35, cheat-sheet PDF, $9) → outline + product_content + listing_copy + qa_review + distribution_post artifacts → exported to `/app/exports/product_35` → ZIP packaging workflow tested → Gumroad listing created (live or final-draft depending on the last operator step).
- **Codex shipped deterministic continuity infrastructure:** `runbooks/SESSION_RECOVERY.md`, sprint closeout tooling, append-only ledgers (`known_issues.md`, `rollback.md`, `commands_run.md`, `verification_results.md`), structured logging helpers in `app/logger.py`, JSONL runtime logs under `logs/`, `scripts/preflight_check.sh`, `scripts/status_snapshot.sh`, environment validation. Read `runbooks/ROADMAP.md` Part 5 for the protocol these implement.
- **Ruflo remains scaffolded but unactivated.** No autonomous swarm. Manual prompts only. Pause was deliberate, pending budget controls + LLM execution semantics + kill-switch enforcement.
- Boundary still holds: Zone A generates artifacts; Zone B owns approvals, money, URLs, publishing.

## Strategic shift the operator wants you to internalize

HYDRA has moved from **infrastructure-first** to **real-world launch + learning**. The dominant value now is signal quality, launch velocity, conversion learning, attribution, and distribution effectiveness — NOT more infrastructure.

The operator has flagged a future direction toward **promotion/distribution agents** (generate, prepare, distribute, track launch effectiveness) — but this must remain controlled, budget-aware, approval-gated, non-spammy. **Do not build autonomous posting.** This is strategic direction, not the next sprint.

## Restraint that is correct, not a bug

The team intentionally did NOT overbuild orchestration, did NOT activate autonomous swarms, did NOT add aggressive automation. Frame is: **controlled AI operating environment**, not uncontrolled autonomous swarm. Preserve this restraint.

## Mandatory inspection (run before evaluating)

```bash
cd /home/jb/dev/hydra
git status
git log --oneline -20
find runbooks -maxdepth 3 -type f | sort
find logs -maxdepth 3 -type f 2>/dev/null | sort
sed -n '1,260p' runbooks/ROADMAP.md
sed -n '1,260p' runbooks/SESSION_RECOVERY.md
ls -la runbooks/sprint_*_handoff.md 2>/dev/null
sed -n '1,260p' "$(ls -t runbooks/sprint_*_handoff.md | head -1)"
sed -n '1,200p' runbooks/known_issues.md
sed -n '1,200p' runbooks/rollback.md
sed -n '1,200p' runbooks/verification_results.md
sed -n '1,200p' README.md
sed -n '1,260p' app/main.py
sed -n '1,200p' app/db.py
test -f app/logger.py && sed -n '1,200p' app/logger.py
./scripts/preflight_check.sh 2>&1 | tail -40
./scripts/status_snapshot.sh 2>&1 | tail -40
docker compose ps
curl -s http://localhost:8000/health
```

If any of those files do not exist, note that explicitly in the evaluation. Do not assume.

## Strategic evaluation (REQUIRED before any coding)

Produce, in this order, plain-prose answers — no fluff:

1. **Inspection summary** — what is actually on disk vs what was claimed in this prompt. Flag any discrepancy.
2. **Project assessment** — production-ready / MVP-ready / mock — has any of this drifted since the last roadmap update?
3. **Launch-readiness assessment** — can the operator ship a second product tomorrow without engineering changes? If not, what is the smallest blocker?
4. **Operational maturity assessment** — score continuity, observability, rollback discipline, boundary integrity.
5. **Biggest current weakness** — one item, named.
6. **Biggest hidden opportunity** — one item, named. (Hint to consider: the `evidence` field already in the DB; product 35's real performance data once a sale lands; second-source confirmation across HN + Reddit.)
7. **Next sprint recommendation** — is Sprint 1.3 (controlled LLM execution layer) still right, or should the next sprint pivot toward **launch learning / attribution / a Reddit collector / conversion tracking** given the strategic shift? Defend the choice with one paragraph against the alternatives.
8. **Do-not-build list** — concrete features that look tempting right now but should be rejected this sprint.

## Session-recovery paragraph (last, mandatory)

Close your evaluation with one paragraph (≤ 120 words) of the form:

> "I read the handoff for sprint <id>. State: <stack health, last verified action>. The next sprint per the roadmap is <next-id> OR <revised-id> because <reason>. Open hazards: <top 3 from known_issues.md>. I am cleared to start because: <handoff complete, verifications green, no boundary or spend regressions>."

If you cannot truthfully write that paragraph, the sprint is not ready and you must say so instead of starting work.

## Constraints

- Do not touch `app/ruflo_bridge.py` boundary contracts without an explicit boundary review section in your eventual sprint handoff.
- Do not introduce LLM calls anywhere except through a single `app/llm.py` client gated by `daily_budget_usd` and `assert_system_can_act("llm_call")`.
- Do not enable autoposting in any community.
- Do not start a new sprint without finishing the handoff for the previous one.
- Do not bypass `scripts/preflight_check.sh`. If it fails, fix the failure first or roll back.

Begin with the inspection block above. Do not code until your strategic evaluation and recovery paragraph are written.

---PROMPT END---
