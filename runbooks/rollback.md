# Rollback Procedures

One section per sprint that introduced an irreversible or risky change. Each section names the exact steps to revert. Append, do not edit prior sections.

> **General code rollback:** `git checkout sprint-<previous-id> && docker compose up -d --build`.
> **General data rollback:** restore the most recent `backups/YYYY-MM-DD/hydra.dump.gz` (Sprint 2.0 introduces backup discipline).

---

### Sprint 1.2

- **Auto-prefilled draft on opportunity approval.** If this misbehaves:
  ```sql
  -- Inside Postgres:
  DELETE FROM products WHERE id = <bad_product_id> AND status = 'draft';
  UPDATE opportunity_candidates SET status = 'new' WHERE id = <opp_id>;
  ```
  No external side-effects; safe to re-run approve afterward.
- **Artifact export.** Files land in `./exports/product_<id>/`. Safe to delete; no DB rows reference them.
- **HN collector.** Inserted rows are normal `OpportunityCandidate` rows; delete by `source = 'HackerNews'` if needed:
  ```sql
  DELETE FROM opportunity_candidates WHERE source = 'HackerNews' AND status = 'new';
  ```
- **Kill switch / budget UI.** Settings page state lives in `system_flags`. To force-reset:
  ```sql
  UPDATE system_flags SET value = 'false' WHERE key = 'hydra:kill';
  UPDATE system_flags SET value = '3'     WHERE key = 'daily_budget_usd';
  ```
- **Volume mount for `./exports`.** Removing the volume in `docker-compose.yml` does not delete files on the host; it only stops the container from seeing them.


### Sprint 1.3

- **Code rollback (single command):**
  ```bash
  git checkout HEAD -- app/main.py app/db.py app/templates/product_edit.html app/templates/revenue.html app/templates/launch.html
  docker compose up -d --build
  ```
- **Schema rollback (only if mandatory; columns are nullable and harmless if left in place):**
  ```sql
  ALTER TABLE revenue_events    DROP COLUMN IF EXISTS source_attribution;
  ALTER TABLE revenue_events    DROP COLUMN IF EXISTS channel_tag;
  ALTER TABLE product_artifacts DROP COLUMN IF EXISTS published_url;
  ALTER TABLE product_artifacts DROP COLUMN IF EXISTS published_at;
  ALTER TABLE product_artifacts DROP COLUMN IF EXISTS channel_tag;
  ```
- **Auto-registered `product_files` rows for product 35** are deletable; the actual exported Markdown remains in `./exports/product_35/`.
### Sprint 1.4 — Controlled LLM Execution Layer

Code rollback:

```bash
git checkout HEAD -- app/db.py app/main.py app/templates/settings.html app/requirements.txt .env.example docker-compose.yml
rm -f app/llm.py scripts/verify_sprint14.sh runbooks/sprint_1.4_handoff.md
docker compose up -d --build
```

Data rollback is optional. The new `llm_calls` table is append-only, nullable, and harmless if left in place.

Only drop it if a clean local reset is required:

```sql
DROP TABLE IF EXISTS llm_calls;
```

Operational rollback:

```bash
curl -u admin:change-me -X POST -F enabled=false http://localhost:8000/settings/kill-switch
curl -u admin:change-me -X POST -F daily_budget_usd=3 http://localhost:8000/settings/budget
```
