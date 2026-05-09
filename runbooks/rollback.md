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
