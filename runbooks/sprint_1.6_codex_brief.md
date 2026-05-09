# Sprint 1.6 Codex Brief — Alembic + Backups + Listings Table

**Sprint:** 1.6
**Complexity:** M (1 day)
**Executor:** Codex-safe
**Depends on:** Sprint 1.5 (DONE)
**Blocks:** Sprint 4.0 (Gumroad API draft creation — first marketplace credential)

---

## Why this sprint exists

Sprint 1.5 introduced five new generation routes. The system still runs `create_all()` on
startup with no migration history. Before Sprint 4.0 lands the first marketplace credential
(Gumroad API token), HYDRA needs:

1. **Alembic** — so column changes are tracked, reversible, and don't require destructive resets.
2. **Backups** — we have never backed up the database. One `docker volume rm` erases everything.
3. **`listings` table** — a multi-platform listings layer so Sprint 4.0 can create Gumroad drafts,
   Sprint 7.0 can add Etsy, and future storefronts (Sellfy, Payhip, Creative Market) slot in
   without schema redesign.

---

## Scope (implement all)

### 1. Alembic baseline

- Install `alembic` in `app/requirements.txt`.
- `alembic init alembic/` inside `/home/jb/dev/hydra/app/`.
- Configure `alembic/env.py` to import `db.Base` and use `DATABASE_URL` from env.
- Generate the baseline migration covering all current tables:
  `opportunity_candidates`, `products`, `product_artifacts`, `product_files`,
  `revenue_events`, `approvals`, `system_flags`, `llm_calls`.
- Update `init_db()` in `db.py` to call `alembic upgrade head` INSTEAD of `create_all()`.
  Keep `_apply_one_shot_migrations()` for the additive ALTER TABLE guards — they are safe
  to run alongside Alembic during Sprint 1.6 to handle the transition.
- Verify: `alembic history` shows one revision; `alembic current` shows that revision as head
  after `dev_up.sh`.

### 2. pg_dump backup script

- Create `scripts/backup_db.sh`:
  - Runs `docker compose exec -T postgres pg_dump -U hydra hydra` piped to
    `backups/YYYY-MM-DD_HH-MM.dump.gz` (gzip compressed).
  - Keeps last 14 dumps; deletes older ones.
  - Prints backup size and path on success.
  - Exit code 0 on success, 1 on failure.
- Create `scripts/restore_db.sh`:
  - Takes one argument: path to a `.dump.gz` file.
  - Prompts "Restore from <path>? This will DROP and recreate the hydra database. [y/N]".
  - On confirmation: drops `hydra` DB, creates fresh, restores from dump.
  - Runs `alembic upgrade head` after restore.
- Create `backups/` directory with a `.gitkeep` and add `backups/*.dump.gz` to `.gitignore`.
- Add a comment in `scripts/backup_db.sh` about adding a cron or systemd timer (operator
  configures this manually after sprint; do not automate it in this sprint).

### 3. `listings` table

New SQLAlchemy model in `db.py`:

```python
class Listing(Base):
    __tablename__ = "listings"

    id            = Column(Integer, primary_key=True)
    product_id    = Column(Integer, ForeignKey("products.id"), nullable=False)
    platform      = Column(Text, nullable=False)   # gumroad | etsy | sellfy | payhip | creative_market
    status        = Column(Text, default="draft")  # draft | live | paused | archived
    external_id   = Column(Text)                   # platform's own product/listing ID
    draft_url     = Column(Text)                   # URL of the draft listing
    live_url      = Column(Text)                   # URL once published (operator enters)
    price_cents   = Column(Integer)                # price at time of listing creation
    currency      = Column(Text, default="USD")
    notes         = Column(Text)
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

Add to `init_db()` / Alembic: this table is created via the Sprint 1.6 Alembic migration
(not `create_all` — that gets replaced by Alembic).

Add a simple read-only view on the product edit page: a "Listings" section below "Files"
showing any `listings` rows for this product (platform, status, draft_url/live_url, created_at).
No creation UI yet — Sprint 4.0 adds that when the Gumroad API client lands.

### 4. Verification script

`scripts/verify_sprint16.sh`:
- `alembic history` shows at least one revision.
- `alembic current` shows the head revision after startup.
- `backup_db.sh` runs without error and produces a `.dump.gz` in `backups/`.
- `listings` table exists with expected columns.
- `/products/<any_id>/edit` renders (listings section present, no crash).
- Existing Sprint 1.4 and 1.5 verify scripts still PASS.

---

## Do NOT add in Sprint 1.6

- Gumroad API client (Sprint 4.0).
- Etsy API client.
- Auto-backup cron/systemd setup.
- Any UI beyond the read-only listings section.
- LLM-backed listing draft creation.
- Any change to the generation routes added in Sprint 1.5.
- Removal of HTTP basic auth.

---

## Files expected to change

- `app/requirements.txt` — add `alembic`.
- `app/db.py` — add `Listing` model; update `init_db()` to use `alembic upgrade head`.
- `app/main.py` — import `Listing`; add listings section to `edit_product` template context.
- `app/templates/product_edit.html` — read-only listings section.
- `app/alembic/` — new directory with `env.py`, `alembic.ini`, `versions/`.
- `scripts/backup_db.sh` — new.
- `scripts/restore_db.sh` — new.
- `scripts/verify_sprint16.sh` — new.
- `backups/.gitkeep` — new.
- `.gitignore` — add `backups/*.dump.gz`.
- `runbooks/sprint_1.6_handoff.md` — new (Codex writes this at end of sprint).
- `runbooks/known_issues.md` — append any new issues.
- `runbooks/verification_results.md` — append Sprint 1.6 row.
- `runbooks/commands_run.md` — append Sprint 1.6 commands.
- `logs/sprints/sprint_history.md` — append closeout entry.

---

## Acceptance criteria

1. `alembic upgrade head` runs cleanly from a fresh DB with no existing tables.
2. `alembic upgrade head` runs cleanly from a DB that already has tables (idempotent).
3. `scripts/backup_db.sh` produces a `.dump.gz` that `scripts/restore_db.sh` can restore.
4. After restore, all existing data is present and HYDRA starts cleanly.
5. `listings` table present with all columns.
6. Product edit page renders a "Listings" section (empty if no rows).
7. `verify_sprint16.sh` PASS.
8. `verify_sprint15.sh` PASS (no regression).
9. `verify_sprint14.sh` PASS (no regression).
10. Sprint 1.6 handoff doc present and complete.

---

## Session recovery for Codex

Before starting, run:

```bash
cd /home/jb/dev/hydra
git status
git log --oneline -5
./scripts/preflight_check.sh
./scripts/verify_sprint15.sh   # confirm 1.5 is green
./scripts/verify_sprint14.sh   # confirm 1.4 is green
```

Read in order:
1. `runbooks/ROADMAP.md` (architecture context)
2. `runbooks/sprint_1.5_handoff.md` (most recent sprint state)
3. `runbooks/known_issues.md` (open hazards)
4. This document (your spec)

Then write one paragraph: "I read the handoff and verified state X, Y, Z. Implementing Sprint 1.6."
Only then begin coding.
