# Session Recovery

Goal: a new operator, Codex session, Claude session, ChatGPT session, or future agent can recover HYDRA safely in under 15 minutes without changing architecture by accident.

## 1. Start With The Boundary

Read these first:

```bash
cd /home/jb/dev/hydra
sed -n '1,220p' README.md
sed -n '1,260p' runbooks/ruflo_boundary.md
sed -n '1,220p' runbooks/ROADMAP.md
```

Rules that matter most:

- Zone A produces proposals and artifacts only.
- Zone B owns approvals, product state, Gumroad URLs, revenue, budgets, kill switch, and future credentials.
- Do not modify SIGNAL scoring or architecture unless the active sprint explicitly says so.
- Do not add autonomous publishing, spending, scraping, or marketplace behavior as a recovery task.

## 2. Inspect Current Project State

```bash
cd /home/jb/dev/hydra
git branch --show-current 2>/dev/null || true
git status --short 2>/dev/null || true
find runbooks -maxdepth 2 -type f | sort
find logs -maxdepth 3 -type f | sort
find scripts -maxdepth 1 -type f | sort
```

Then run:

```bash
./scripts/status_snapshot.sh
```

If files are dirty, assume they are intentional until proven otherwise. Do not revert user or agent work without explicit instruction.

## 3. Verify Docker And Services

```bash
./scripts/dev_up.sh
./scripts/preflight_check.sh
curl http://localhost:8000/health
```

Expected:

- Docker is reachable.
- Postgres and Redis containers are healthy.
- Postgres accepts `pg_isready`.
- Redis answers `PING`.
- FastAPI `/health` returns healthy JSON.

## 4. Identify The Current Sprint

Use this order:

1. Read the newest entry in `logs/sprints/sprint_history.md`.
2. Read `runbooks/sprint1_handoff.md` and any newer `runbooks/sprint_*_handoff.md`.
3. Read the immediate next sprint recommendation in `runbooks/ROADMAP.md`.
4. Read `runbooks/known_issues.md`.

If these disagree, stop and write a short status note for the operator before implementing.

## 5. Review Ledgers

```bash
tail -80 logs/sprints/sprint_history.md
tail -80 logs/verification/verification_history.md
tail -20 logs/runtime/runtime_events.jsonl
tail -20 logs/revenue/revenue_events.jsonl
```

Append to ledgers; do not rewrite history. If a prior entry is wrong, add a correcting entry with a timestamp.

## 6. Resume Interrupted Work Safely

Before editing:

- State the active sprint objective in one sentence.
- Classify the task using `runbooks/ROADMAP.md` Part 4.
- Confirm the task is Codex-safe, Claude-required, or Human-required.
- Confirm the task does not change Zone A / Zone B boundaries.
- Confirm the task does not touch scoring unless explicitly requested.

Then work in small patches and verify with scripts.

## 7. Avoid Architecture Drift

Do not add:

- Kubernetes
- React or Next.js
- Celery, Temporal, LangChain, LangGraph
- Real Gumroad API integration
- Real marketplace publishing
- Autonomous social posting
- New scoring philosophy
- New AI orchestration

During recovery, prefer docs, scripts, logs, and deterministic checks.

## 8. Validate Acceptance Criteria

For any sprint:

```bash
chmod +x scripts/*.sh
./scripts/validate_env.sh
./scripts/preflight_check.sh
```

Run feature-specific verification scripts if present:

```bash
find scripts -maxdepth 1 -name 'verify_*.sh' -print -exec {} \;
```

Record the result:

```bash
./scripts/sprint_closeout.sh
```

## 9. Recovery Paragraph

Before handing off, write a paragraph like this:

> I recovered HYDRA from `/home/jb/dev/hydra`. The stack is <healthy/unhealthy>. The latest sprint ledger entry is <entry>. The active roadmap recommendation is <sprint>. Known hazards are <top issues>. I changed only <scope>. Verification <passed/failed with reason>.

If you cannot truthfully write this paragraph, recovery is not complete.
