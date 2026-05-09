# Sprint <ID> Handoff — <SHORT TITLE>

**Sprint:** <ID> (e.g. 1.3, 2.1)
**Branch:** `sprint/<id>-<slug>`
**Started:** YYYY-MM-DD
**Completed:** YYYY-MM-DD
**Executor:** <Codex | Claude | Operator | mixed>
**Boundary touched:** <yes / no — if yes, summarize>
**Spend touched:** <yes / no — if yes, summarize>

> Copy this file to `runbooks/sprint_<id>_handoff.md` and fill in every section. Delete sections only if they truly do not apply, and add a note saying why.

---

## 1. Inspection summary

What was on disk at the start of the sprint? Reference the previous handoff (`sprint_<prev-id>_handoff.md`) and any deltas discovered.

- Working tree: <clean | dirty — list>
- `docker compose ps` at start: <output>
- `git log --oneline -5`:
  ```
  <paste>
  ```

## 2. Objective (from ROADMAP.md)

Quote the sprint's Objective and Features lines from `runbooks/ROADMAP.md`. Note any approved deviation from the roadmap, with a one-line reason.

## 3. Files changed

### Modified
- `path/to/file` — one-line summary

### Created
- `path/to/file` — one-line summary

### Deleted
- `path/to/file` — reason

## 4. Schema changes

If any: list the migration file(s), the table(s) and column(s) affected, and the Alembic command(s) to apply.

> Forbidden if Sprint 2.0 has not shipped: schema changes outside `init_db()`'s `create_all`.

## 5. Commands run

Append-only log. Useful commands only — not every shell line.

```
<command>
<command>
```

## 6. Verification results

- `scripts/verify_<feature>.sh` output: <PASS | FAIL — tail>
- `curl /health`: <status>
- End-to-end manual click-through (operator console): <PASS | FAIL — what was clicked>
- Spend during verification: <$X.YZ recorded in `llm_calls`>

## 7. Known issues

Cross-link each item to `runbooks/known_issues.md`.

- [ ] <description> — <severity> — <file:line if applicable>

## 8. Rollback procedure

The exact steps to revert this sprint without data loss. Copy into `runbooks/rollback.md` under a new heading `### Sprint <id>`.

```bash
# Code rollback
git checkout sprint-<previous-id>
docker compose up -d --build

# Data rollback (if any irreversible change)
gunzip -c backups/YYYY-MM-DD/hydra.dump.gz | docker compose exec -T postgres pg_restore -U hydra -d hydra --clean --if-exists
```

## 9. Boundary review

Required if this sprint added or touched any Zone A path.

- [ ] Did any new code path expose marketplace credentials to Zone A? (Must be NO.)
- [ ] Did any new code path allow Zone A to publish, spend, or modify state? (Must be NO.)
- [ ] Did any new code path automate posting in a moderated community? (Must be NO until further notice.)
- [ ] Did any new code path add an LLM call that bypasses `app/llm.py` budget guard? (Must be NO.)

If any answer is YES, the sprint is not done. Fix or revert.

## 10. Spend review

- Daily budget cap at end of sprint: $<X>
- Total spend during sprint development: $<X>
- Routes added that can spend: <list>
- Routes added that are gated by `assert_system_can_act`: <list>

## 11. Operator-facing changes

If anything changed that an operator clicking through the console would notice, summarize here. This becomes the `runbooks/launch_day.md` update for the sprint.

## 12. Recommended next sprint

Per `runbooks/ROADMAP.md` critical path. If deviating, justify in one paragraph.

- Recommended: Sprint <next-id> — <name>
- Blocking issues for that sprint: <none | list>

## 13. Session-recovery paragraph

The paragraph the *next* agent should read first. One paragraph, ≤ 120 words, plain English:

> "I read the handoff for sprint <id>. State: <stack health, last verified action>. The next sprint per the roadmap is <next-id>. Open hazards: <top 3 items from known_issues.md>. I am cleared to start because: <handoff complete, verification scripts green, no boundary or spend regressions>."

If you cannot truthfully write this paragraph, the sprint is not complete.

---

_Template version: 1.0. Update with each lesson learned._

---

# Copy-Paste Sprint Brief

Use this shorter version when opening a new agent session.

## Sprint Name

`Sprint <ID> — <name>`

## Objective

<One paragraph. Include what must not change.>

## Current State

- Stack health: <unknown | healthy | failing>
- Latest sprint ledger entry: <summary>
- Known issues reviewed: <yes/no>
- Boundary touched: <yes/no>

## Tasks

- [ ] <task>
- [ ] <task>
- [ ] <task>

## Acceptance Criteria

- [ ] <criterion>
- [ ] <criterion>
- [ ] <criterion>

## Commands To Run

```bash
cd /home/jb/dev/hydra
chmod +x scripts/*.sh
./scripts/status_snapshot.sh
./scripts/validate_env.sh
./scripts/preflight_check.sh
```

## Verification Steps

- <manual or scripted check>
- <manual or scripted check>

## Files Changed

- `<path>` — <summary>

## Known Issues

- <issue or none>

## Rollback Notes

```bash
<exact rollback command or "No rollback needed; docs/scripts only.">
```

## Next Sprint Recommendations

- <recommendation>
