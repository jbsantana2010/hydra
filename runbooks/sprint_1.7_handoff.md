# Sprint 1.7 Handoff — Marketplace Intelligence v1

Date: 2026-05-10  
Executor: Codex  
Source of truth: `/home/jb/dev/hydra`

## Implementation Summary

Claude's partial Sprint 1.7 work was merged from the OneDrive copy into the real WSL project with surgical edits only. The WSL project now supports manual/CSV marketplace research imports, market research runs, market research items, guarded LLM pattern extraction, and operator-reviewed opportunity generation from extracted patterns.

No external scraping, marketplace APIs, publishing automation, or marketplace credentials were added.

## Files Changed

- `app/alembic/versions/0003_sprint17_market_intelligence.py`
- `app/db.py`
- `app/llm.py`
- `app/main.py`
- `app/templates/base.html`
- `app/templates/market_research_list.html`
- `app/templates/market_research_detail.html`
- `scripts/sample_research.csv`
- `scripts/verify_sprint17.sh`
- `runbooks/ROADMAP.md`
- `runbooks/sprint_1.7_codex_brief.md`
- `runbooks/sprint_1.7_handoff.md`
- `runbooks/verification_results.md`
- `runbooks/commands_run.md`
- `runbooks/known_issues.md`
- `logs/sprints/sprint_history.md`

## Commands Run

```bash
cd /home/jb/dev/hydra
git status
git log --oneline -10
./scripts/preflight_check.sh
bash scripts/verify_sprint151.sh
LIVE=1 bash scripts/verify_sprint151.sh
./scripts/verify_sprint15.sh
bash scripts/verify_sprint16.sh
find /mnt/c/Users/jbsan/OneDrive/Documents/New\ project\ 2/hydra -maxdepth 3 -type f | sort
python3 -m py_compile app/main.py app/db.py app/llm.py
docker compose run --rm --no-deps hydra-console python -m py_compile /app/main.py /app/db.py /app/llm.py
./scripts/backup_db.sh
docker compose run --rm hydra-console alembic upgrade head
docker compose run --rm hydra-console alembic current -v
docker compose down
docker compose up -d --build
./scripts/preflight_check.sh
bash scripts/verify_sprint17.sh
LIVE=1 bash scripts/verify_sprint17.sh
bash scripts/verify_sprint16.sh
bash scripts/verify_sprint15.sh
```

## Verification Results

- Static syntax check: PASS
- Container syntax check: PASS
- Alembic current: PASS, current revision is `0003 (head)`
- `./scripts/preflight_check.sh`: PASS
- `bash scripts/verify_sprint17.sh`: PASS, 30/30
- `LIVE=1 bash scripts/verify_sprint17.sh`: PASS, 38/38
- `bash scripts/verify_sprint16.sh`: PASS, 43/43 with 3 live DB checks skipped because `LIVE_DB=1` was not set
- `bash scripts/verify_sprint15.sh`: FAIL on preexisting generation guard-path checks; see known issues

## Manual UI Smoke

Manual smoke used `scripts/sample_research.csv` against `/market-research`.

- Market Research nav link renders.
- Created research run `Manual Smoke 1.7D`.
- Imported 10 sample research items.
- Analyze created 13 `market_patterns`.
- Generate opportunities created 5 `opportunity_candidates`.
- Generated candidates have `source='market_intelligence'` and `status='pending_review'`.
- Generated candidates appear in `/opportunities`; operator approval remains required before product generation.

## Known Issues

- Sprint 1.5 verification still fails on generation guard-path checks. This was present before Sprint 1.7 merge and was not changed in this sprint.
- Anthropic primary LLM calls returned 404 in this environment during smoke testing. OpenAI fallback handled Sprint 1.7 pattern extraction after the market-intelligence completion budget was widened.
- Sprint 1.7 verification and manual smoke leave local test research runs/items/patterns/opportunities in the development database.

## Rollback Notes

To roll back Sprint 1.7:

```bash
cd /home/jb/dev/hydra
./scripts/backup_db.sh
docker compose run --rm hydra-console alembic downgrade 0002
```

Then revert the Sprint 1.7 files listed above. Do not roll back by copying the OneDrive project over WSL.

## Next Sprint Recommendation

Sprint 1.8 should improve launch experiment throughput without adding external scraping or marketplace automation. Recommended focus: marketplace pattern review UX, cleanup of verification-created sample runs, and product packaging improvements for market-intelligence-derived opportunities.
