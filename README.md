# HYDRA

HYDRA is an AI-powered micro-venture factory scaffold with deterministic operational continuity tooling.

Sprint 1 builds the local Zone B console:

- Postgres 16 for durable business state
- Redis 7 placeholder for later queues/cache
- FastAPI + Jinja2 console
- Mock SIGNAL scan with deterministic opportunity scoring
- Operator approval flow
- Product record creation
- Product edit and Gumroad URL storage
- Manual revenue ledger
- Kill switch and daily budget settings
- Ruflo artifact import
- Ruflo prompt helpers with a hard Zone A/Zone B boundary
- Operational ledgers and recovery scripts so agents can resume safely after interruptions

## Quick Start

```bash
cd /home/jb/dev/hydra
chmod +x scripts/*.sh
./scripts/dev_up.sh
curl http://localhost:8000/health
python3 scripts/seed_mock_signals.py
```

Open the console:

```text
http://localhost:8000/opportunities
```

Login with:

```text
admin / change-me
```

## Zone Boundary

Ruflo is Zone A: creative and generative swarm work. It produces proposals, critiques, outlines, listing drafts, and other artifacts.

HYDRA is Zone B: deterministic business logic. It stores records, controls approvals, owns marketplace credentials, tracks money, and publishes only after operator approval.

Ruflo must never hold Gumroad credentials, spend money, publish listings, or make final approval decisions.

## Local Services

- FastAPI console: `http://localhost:8000`
- Postgres: `localhost:5432`
- Redis: `localhost:6379`

Default local database credentials:

```text
POSTGRES_DB=hydra
POSTGRES_USER=hydra
POSTGRES_PASSWORD=hydra
```

Default console credentials:

```text
HYDRA_BASIC_USER=admin
HYDRA_BASIC_PASS=change-me
```

## Continuity Workflow

Before starting or resuming a sprint:

```bash
cd /home/jb/dev/hydra
chmod +x scripts/*.sh
./scripts/status_snapshot.sh
./scripts/validate_env.sh
./scripts/preflight_check.sh
```

When closing a sprint or handoff point:

```bash
./scripts/sprint_closeout.sh
```

Read these continuity docs:

- `runbooks/SESSION_RECOVERY.md` — recovery procedure for a new session/model/operator
- `runbooks/ROADMAP.md` — sprint phases, dependencies, risks, task classification, and guardrails
- `runbooks/SPRINT_TEMPLATE.md` — reusable sprint handoff template
- `logs/sprints/sprint_history.md` — append-only sprint ledger
- `logs/verification/verification_history.md` — append-only human-readable verification ledger
- `logs/runtime/runtime_events.jsonl` — append-only machine-readable runtime events
- `logs/revenue/revenue_events.jsonl` — append-only revenue mirror; database remains source of truth

Operational rule: append to ledgers, never rewrite history. If a prior entry is wrong, add a correcting entry with a new timestamp.

## Sprint Workflow

1. Read `runbooks/SESSION_RECOVERY.md`.
2. Identify the active sprint from `logs/sprints/sprint_history.md` and `runbooks/ROADMAP.md`.
3. Classify the task as Codex-safe, Claude-required, or Human-required.
4. Implement only the requested sprint scope.
5. Run preflight and feature verification.
6. Append a closeout snapshot with `scripts/sprint_closeout.sh`.

## What This Is Not Yet

Sprint 1.1 does not include real scrapers, paid APIs, Gumroad publishing, automated revenue ingestion, or Ruflo automation. Those are intentionally left as explicit next steps.
