# Sprint History

Append-only sprint ledger. Add newest entries at the bottom so shell tools can tail the file.

Entry format:

```markdown
## YYYY-MM-DDTHH:MM:SSZ - Sprint <id/name>

- Commit: `<git sha or unknown>`
- Executor: <Codex | Claude | Operator | mixed>
- Files changed:
  - `<path>`
- Verification:
  - <summary>
- Known issues:
  - <summary or none>
- Next:
  - <recommended next step>
```

---

## 2026-05-08T00:00:00Z - Sprint 1.2 Baseline

- Commit: `unknown`
- Executor: mixed
- Files changed:
  - `runbooks/ROADMAP.md`
  - `runbooks/SPRINT_TEMPLATE.md`
  - Sprint 1.2 launch-support files already present in the repo
- Verification:
  - See `runbooks/verification_results.md` for the Sprint 1.2 verification table.
- Known issues:
  - See `runbooks/known_issues.md`.
- Next:
  - Continue with deterministic operational continuity tooling before any architecture or SIGNAL work.

## 2026-05-09T00:01:17Z - Sprint Closeout Snapshot

- Commit: `unknown`
- Branch: `unknown`
- Executor: Codex/operator
- Files changed:
  - none
- Verification:
```text
# Verification History

Append-only human-readable verification ledger. Newest entries go at the bottom.

Entry format:

```markdown
## YYYY-MM-DDTHH:MM:SSZ - <check name>

- Command: `<command>`
- Result: PASS | FAIL | WARN
- Summary: <short output summary>
```

---

## 2026-05-08T00:00:00Z - Sprint 1.2 Baseline

- Command: `scripts/verify_sprint12.sh && scripts/verify_url_warnings.sh`
- Result: PASS
- Summary: See `runbooks/verification_results.md`.
```
- Known issues:
  - See `runbooks/known_issues.md`.
- Next:
  - Follow `runbooks/ROADMAP.md` immediate next sprint recommendation unless operator overrides.

## 2026-05-10T20:59:49Z - Sprint 1.7 Closeout (Marketplace Intelligence v1)

- Commit: `uncommitted at closeout`
- Branch: `main`
- Executor: Codex
- Source of truth: `/home/jb/dev/hydra`
- Summary:
  - Merged Claude's Sprint 1.7 OneDrive work into WSL without overwriting the project.
  - Added market research runs, items, patterns, CSV import, guarded LLM pattern extraction, and opportunity generation.
  - Preserved Zone B ownership and did not add scraping, marketplace APIs, auto-publishing, credentials, or autonomous behavior.
- Verification:
  - `python3 -m py_compile app/main.py app/db.py app/llm.py` — PASS.
  - `docker compose run --rm --no-deps hydra-console python -m py_compile /app/main.py /app/db.py /app/llm.py` — PASS.
  - `docker compose run --rm hydra-console alembic current -v` — PASS, `0003 (head)`.
  - `./scripts/preflight_check.sh` — PASS.
  - `bash scripts/verify_sprint17.sh` — PASS, 30/30.
  - `LIVE=1 bash scripts/verify_sprint17.sh` — PASS, 38/38.
  - `bash scripts/verify_sprint16.sh` — PASS.
  - `bash scripts/verify_sprint15.sh` — FAIL on preexisting generation guard-path checks.
- Manual smoke:
  - CSV import created 10 items.
  - Analyze created 13 market patterns.
  - Generate opportunities created 5 pending-review opportunity candidates.
- Known issues:
  - See `runbooks/known_issues.md`.
- Next:
  - Sprint 1.8 should focus on marketplace intelligence review UX and product packaging improvements, with no external scraping or marketplace automation.

## 2026-05-09T03:55:00Z - Sprint 1.4 Controlled LLM Execution Layer

- Commit: `unknown`
- Executor: Codex
- Files changed:
  - `app/llm.py`
  - `app/db.py`
  - `app/main.py`
  - `app/templates/settings.html`
  - `app/requirements.txt`
  - `.env.example`
  - `docker-compose.yml`
  - `scripts/verify_sprint14.sh`
  - `runbooks/sprint_1.4_handoff.md`
  - `runbooks/known_issues.md`
  - `runbooks/verification_results.md`
  - `runbooks/commands_run.md`
  - `runbooks/rollback.md`
- Verification:
  - `python3 -m py_compile app/main.py app/db.py app/llm.py` PASS.
  - `./scripts/dev_up.sh` PASS.
  - `./scripts/verify_sprint14.sh` PASS without API keys, proving fallback and guard behavior.
- Known issues:
  - Real provider smoke is conditional on API keys.
  - Cost accounting is conservative unless provider usage metadata is returned.
- Next:
  - Choose between launch experiments, Reddit collector, packaging improvements, or attribution/source-weight learning. Recommendation: packaging improvements unless a Reddit niche list is ready.

## 2026-05-09T00:01:46Z - Sprint Closeout Snapshot

- Commit: `unknown`
- Branch: `unknown`
- Executor: Codex/operator
- Files changed:
  - none
- Verification:
  ```text
  # Verification History
  
  Append-only human-readable verification ledger. Newest entries go at the bottom.
  
  Entry format:
  
  ~~~markdown
  ## YYYY-MM-DDTHH:MM:SSZ - <check name>
  
  - Command: `<command>`
  - Result: PASS | FAIL | WARN
  - Summary: <short output summary>
  ~~~
  
  ---
  
  ## 2026-05-08T00:00:00Z - Sprint 1.2 Baseline
  
  - Command: `scripts/verify_sprint12.sh && scripts/verify_url_warnings.sh`
  - Result: PASS
  - Summary: See `runbooks/verification_results.md`.
  
  ## 2026-05-09T00:01:00Z - Operational Continuity Scripts
  
  - Command: `./scripts/preflight_check.sh && ./scripts/status_snapshot.sh && ./scripts/validate_env.sh && ./scripts/sprint_closeout.sh`
  - Result: PASS
  - Summary: Docker, Postgres, Redis, and FastAPI were reachable. Environment defaults validated from `.env.example`. Sprint closeout appended to the sprint ledger.
  ```
- Known issues:
  - See `runbooks/known_issues.md`.
- Next:
  - Follow `runbooks/ROADMAP.md` immediate next sprint recommendation unless operator overrides.

## 2026-05-09T01:27:52Z - Sprint Closeout Snapshot

- Commit: `dce4399`
- Branch: `main`
- Executor: Codex/operator
- Files changed:
- `?? exports/product_35/`
- `?? products/`
- `?? ruflo/`
- Verification:
  ```text
  # Verification History
  
  Append-only human-readable verification ledger. Newest entries go at the bottom.
  
  Entry format:
  
  ~~~markdown
  ## YYYY-MM-DDTHH:MM:SSZ - <check name>
  
  - Command: `<command>`
  - Result: PASS | FAIL | WARN
  - Summary: <short output summary>
  ~~~
  
  ---
  
  ## 2026-05-08T00:00:00Z - Sprint 1.2 Baseline
  
  - Command: `scripts/verify_sprint12.sh && scripts/verify_url_warnings.sh`
  - Result: PASS
  - Summary: See `runbooks/verification_results.md`.
  
  ## 2026-05-09T00:01:00Z - Operational Continuity Scripts
  
  - Command: `./scripts/preflight_check.sh && ./scripts/status_snapshot.sh && ./scripts/validate_env.sh && ./scripts/sprint_closeout.sh`
  - Result: PASS
  - Summary: Docker, Postgres, Redis, and FastAPI were reachable. Environment defaults validated from `.env.example`. Sprint closeout appended to the sprint ledger.
  ```
- Known issues:
  - See `runbooks/known_issues.md`.
- Next:
  - Follow `runbooks/ROADMAP.md` immediate next sprint recommendation unless operator overrides.


## 2026-05-09T01:50:00Z - Sprint 1.3 Closeout (Launch Learning v1)

- Commit: `unknown` (uncommitted at write time; tag `sprint-1.3` recommended after operator review)
- Branch: `main`
- Executor: Claude (with operator-approved pivot)
- Files changed:
  - `app/main.py`
  - `app/db.py`
  - `app/templates/product_edit.html`
  - `app/templates/revenue.html`
  - `app/templates/launch.html`
  - `.gitignore` (new)
  - `scripts/verify_sprint13.sh` (new)
  - `scripts/state_inspect.sh` (new)
  - `runbooks/sprint_1.3_handoff.md` (new)
  - `runbooks/known_issues.md` (append)
  - `runbooks/verification_results.md` (append)
  - `runbooks/commands_run.md` (append)
  - `runbooks/rollback.md` (append)
  - `runbooks/launch_day.md` (append)
- Verification:
  - `scripts/verify_sprint13.sh` — ALL PASS (13/13).
- Known issues:
  - Legacy duplicate rows in `product_files` (product 34) block a unique-index migration; deferred to Sprint 2.0.
- Next:
  - Sprint 1.4 — Controlled LLM Execution Layer (originally-planned 1.3). See `runbooks/ROADMAP.md` Sprint 1.4 plan.

## 2026-05-09T03:34:14Z - Sprint Closeout Snapshot

- Commit: `dce4399`
- Branch: `main`
- Executor: Codex/operator
- Files changed:
- ` M app/db.py`
- ` M app/main.py`
- ` M app/templates/launch.html`
- ` M app/templates/product_edit.html`
- ` M app/templates/revenue.html`
- ` M logs/sprints/sprint_history.md`
- ` M runbooks/ROADMAP.md`
- ` M runbooks/commands_run.md`
- ` M runbooks/known_issues.md`
- ` M runbooks/launch_day.md`
- ` M runbooks/rollback.md`
- ` M runbooks/verification_results.md`
- `?? .gitignore`
- `?? runbooks/CLAUDE_RESUME_PROMPT.md`
- `?? runbooks/sprint_1.3_handoff.md`
- `?? scripts/state_inspect.sh`
- `?? scripts/verify_sprint13.sh`
- Verification:
  ```text
  # Verification History
  
  Append-only human-readable verification ledger. Newest entries go at the bottom.
  
  Entry format:
  
  ~~~markdown
  ## YYYY-MM-DDTHH:MM:SSZ - <check name>
  
  - Command: `<command>`
  - Result: PASS | FAIL | WARN
  - Summary: <short output summary>
  ~~~
  
  ---
  
  ## 2026-05-08T00:00:00Z - Sprint 1.2 Baseline
  
  - Command: `scripts/verify_sprint12.sh && scripts/verify_url_warnings.sh`
  - Result: PASS
  - Summary: See `runbooks/verification_results.md`.
  
  ## 2026-05-09T00:01:00Z - Operational Continuity Scripts
  
  - Command: `./scripts/preflight_check.sh && ./scripts/status_snapshot.sh && ./scripts/validate_env.sh && ./scripts/sprint_closeout.sh`
  - Result: PASS
  - Summary: Docker, Postgres, Redis, and FastAPI were reachable. Environment defaults validated from `.env.example`. Sprint closeout appended to the sprint ledger.
  ```
- Known issues:
  - See `runbooks/known_issues.md`.
- Next:
  - Follow `runbooks/ROADMAP.md` immediate next sprint recommendation unless operator overrides.
