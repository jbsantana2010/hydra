# Sprint 1.7 Codex Brief — Reddit Collector + Celery Scheduler

**Sprint:** 1.7  
**Classification:** Codex-safe (no LLM prompt engineering, no marketplace auth, no UI redesign)  
**Estimated effort:** M (1-2 days for a focused Codex session)  
**Depends on:** Sprint 1.6 complete (Alembic in place, DB stable)  
**Unlocks:** Sprint 2.0 (full automated signal pipeline end-to-end)

---

## Mission

Sprint 1.5 gave HYDRA five generation routes. Sprint 1.6 gave it schema discipline.  
Sprint 1.7 gives HYDRA its **second signal source** (Reddit) and a **lightweight background scheduler** so signal collection runs on a cron instead of operator button-presses.

At the end of this sprint, HYDRA can wake up every N hours, collect from HN + Reddit, score candidates, and flag new approvals — without a human at the keyboard.

---

## Context: How HYDRA Works (read this before touching anything)

```
Zone A (READ ONLY for LLM)        Zone B (FastAPI + Postgres + Redis)
─────────────────────────────     ──────────────────────────────────────
Ruflo / Claude / Codex            app/main.py    — FastAPI routes
                                  app/db.py      — SQLAlchemy models
                                  app/llm.py     — guarded LLM client
                                  app/signal_engine.py — SIGNAL scoring
```

**Safety rules you must not break:**
1. **Kill switch first.** Every action that calls an external API or LLM must call `assert_system_can_act(action_name)` before doing anything.
2. **LLM calls through `call_llm_json()` only.** Never call `anthropic` or `openai` SDKs directly.
3. **No marketplace credentials in Zone A.** Scheduler may read DB but never writes listing prices or posts.
4. **`init_db()` is Alembic-managed** since Sprint 1.6. New tables go in a new migration file under `app/alembic/versions/`. Never call `Base.metadata.create_all()`.

---

## Deliverables

### 1. Reddit Collector (`app/reddit_collector.py` — new file)

Collect top posts from configurable subreddits via the Reddit public JSON API (no OAuth required for read-only public posts).

```python
REDDIT_SUBREDDITS = [
    "SideProject", "Entrepreneur", "MachineLearning",
    "learnprogramming", "selfhosted", "nocode",
    "digitalnomad", "passive_income",
]
REDDIT_MAX_POSTS = 10  # per subreddit per run
REDDIT_BASE_URL = "https://www.reddit.com/r/{sub}/hot.json"
```

**Implementation requirements:**

- Use `httpx.Client` with `timeout=10.0` and `headers={"User-Agent": "HYDRA/1.7 signal-collector"}`.
- Parse fields: `title`, `score` (upvotes), `num_comments`, `url`, `selftext` (body snippet), `subreddit`.
- Reuse `_hn_classify()` from `main.py` to classify each post — same vertical + format logic, same LLM gate.
- Reuse `calculate_score()` from `signal_engine.py`.
- Return a list of `OpportunityCandidate`-compatible dicts (same keys as `_hn_to_candidate()`).
- `demand_velocity` formula: `min(100, score * 0.8 + num_comments * 1.2)`.
- Set `source="Reddit"`, `cross_source_confirmation=25` (single source, slightly lower than HN).
- Evidence string format: `"Reddit r/{subreddit} post '{title}' — {score} upvotes, {num_comments} comments. Link: {url}"`.

**Function signature:**
```python
def collect_reddit(db=None, subreddits: list[str] | None = None) -> list[dict]:
    """Fetch hot posts from each subreddit and return scored candidate dicts."""
```

**Error handling:** Per-subreddit try/except — one subreddit failing must not abort the rest.

### 2. FastAPI route: `POST /opportunities/collect/reddit`

Mirror the existing `POST /opportunities/collect/hn` pattern exactly:

```python
@app.post("/opportunities/collect/reddit")
def collect_reddit_endpoint(subreddits: str = Form("")):
    """Fetch Reddit posts and seed candidates. subreddits = comma-separated list."""
```

- Call `assert_system_can_act("collect_reddit")` first.
- Parse `subreddits` form field as comma-separated list; fall back to `REDDIT_SUBREDDITS` default.
- Use `session_scope()` to dedup-insert, same pattern as `collect_hn`.
- Return JSON `{"source": "Reddit", "fetched": N, "inserted": M, "skipped": K, ...}`.

### 3. Celery scheduler (`app/celery_app.py` — new file)

```python
from celery import Celery
from celery.schedules import crontab

celery = Celery("hydra", broker=os.getenv("REDIS_URL", "redis://redis:6379/0"))
celery.conf.timezone = "UTC"

celery.conf.beat_schedule = {
    "collect-hn-every-6h": {
        "task": "tasks.collect_hn_task",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "collect-reddit-every-6h": {
        "task": "tasks.collect_reddit_task",
        "schedule": crontab(minute=30, hour="*/6"),
    },
}
```

### 4. Celery tasks (`app/tasks.py` — new file)

```python
from celery_app import celery
from db import session_scope, OpportunityCandidate, is_kill_switch_active
from signal_engine import calculate_score
import httpx

@celery.task(name="tasks.collect_hn_task")
def collect_hn_task(query: str = "AI"):
    if is_kill_switch_active():
        return {"blocked": True, "reason": "kill switch active"}
    # call the same logic as POST /opportunities/collect/hn
    # import the helper from main.py or refactor into a shared module

@celery.task(name="tasks.collect_reddit_task")
def collect_reddit_task():
    if is_kill_switch_active():
        return {"blocked": True, "reason": "kill switch active"}
    # call reddit_collector.collect_reddit()
```

**Important:** Tasks must check `is_kill_switch_active()` as the FIRST line. Budget check is informational only in tasks (no per-call LLM budget enforcement needed — the individual `call_llm_json()` calls already enforce it).

### 5. `docker-compose.yml` additions

Add two new services after the existing `hydra-console`:

```yaml
  celery-worker:
    build: ./app
    command: celery -A celery_app worker --loglevel=info --concurrency=2
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - ./app:/app

  celery-beat:
    build: ./app
    command: celery -A celery_app beat --loglevel=info
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - ./app:/app
```

Redis is already in `docker-compose.yml`. No new infrastructure needed.

### 6. Alembic migration: `0003_sprint17_scheduler_log.py`

Add a `scheduler_runs` table to track each background collection run:

```python
op.create_table(
    "scheduler_runs",
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("task_name", sa.Text, nullable=False),
    sa.Column("status", sa.Text),          # success | error | blocked
    sa.Column("inserted", sa.Integer, server_default="0"),
    sa.Column("skipped", sa.Integer, server_default="0"),
    sa.Column("error_detail", sa.Text),
    sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
    sa.Column("finished_at", sa.DateTime),
)
```

Add `SchedulerRun` ORM model to `db.py`. Tasks write a row to this table on start and update on finish.

### 7. `requirements.txt` additions

```
celery==5.3.6
redis==5.0.3
```

### 8. `scripts/verify_sprint17.sh`

Write a verification script following the exact pattern of `verify_sprint16.sh`. Must cover:

- `app/reddit_collector.py` exists and has `collect_reddit()` function
- `app/celery_app.py` exists, defines `beat_schedule` with both tasks
- `app/tasks.py` exists, both tasks check kill switch first
- `docker-compose.yml` has `celery-worker` and `celery-beat` services
- `app/alembic/versions/0003_sprint17_scheduler_log.py` exists with correct revision chain
- `db.py` has `SchedulerRun` model
- `requirements.txt` has `celery` and `redis`
- Python syntax check on all new files
- Optional `LIVE_DB=1` check: `celery-worker` container responds to `celery inspect ping`

---

## Files to Create

```
app/reddit_collector.py
app/celery_app.py
app/tasks.py
app/alembic/versions/0003_sprint17_scheduler_log.py
scripts/verify_sprint17.sh
runbooks/sprint_1.7_handoff.md
```

## Files to Modify

```
app/db.py              Add SchedulerRun model
app/main.py            Add POST /opportunities/collect/reddit route
app/requirements.txt   Add celery==5.3.6, redis==5.0.3
docker-compose.yml     Add celery-worker and celery-beat services
```

---

## Acceptance Criteria

All must pass before the sprint is considered complete:

- [ ] `bash scripts/verify_sprint17.sh` exits 0 with 0 FAIL
- [ ] `docker compose up -d` starts without errors, including celery-worker and celery-beat
- [ ] `POST /opportunities/collect/reddit` (form: subreddits=SideProject) returns JSON with `inserted >= 0`
- [ ] Kill switch ON → `POST /opportunities/collect/reddit` returns `{"blocked": true}`
- [ ] `celery -A celery_app inspect ping` responds from worker
- [ ] `alembic -c app/alembic.ini current` shows `0003 (head)`
- [ ] `scheduler_runs` table exists in DB
- [ ] All existing Sprint 1.5 + 1.6 verification checks still pass

---

## Session Recovery

If you are a Codex session that just loaded this brief:

1. `cd /home/jb/dev/hydra`
2. `git log --oneline -5` — confirm Sprint 1.6 is committed
3. `docker compose ps` — confirm all services are running
4. `alembic -c app/alembic.ini current` — should show `0002`
5. Read `app/main.py` lines 1-40 (imports) and search for `collect_hn` to understand the pattern you must mirror
6. Read `app/db.py` lines 1-20 and the `init_db()` function to understand the Alembic integration
7. Start with `app/reddit_collector.py`, then `app/tasks.py`, then `app/celery_app.py`, then migration, then docker-compose

Do not start the verify script until all implementation files are written.

---

## What NOT to Do

- Do not call `anthropic` or `openai` directly — use `call_llm_json()` only
- Do not add OAuth to Reddit collector — public JSON API is sufficient and has no credentials
- Do not add new UI beyond the existing "Collect from Reddit" button (one `<form>` on the opportunities page)
- Do not refactor existing routes — only add new ones
- Do not break the Zone A / Zone B boundary
- Do not use `Base.metadata.create_all()` — use Alembic migrations only
