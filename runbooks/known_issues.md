# Known Issues

Append-only. New entries on top with date and sprint id. Resolved entries get a `~~strikethrough~~` and `(resolved <sprint-id>)` suffix; do not delete.

Format:
```
- YYYY-MM-DD [sprint <id>] **<severity>** — <description>. <file:line | route | symptom>. <mitigation in place>.
```

Severities: `low` / `medium` / `high`.

---

- 2026-05-08 [sprint 1.2] **medium** — `init_db()` runs `create_all()`; column changes will need manual migration or destructive reset. `app/db.py:init_db`. Plan: Sprint 2.0 baselines Alembic.
- 2026-05-08 [sprint 1.2] **medium** — HTTP basic auth, single user, no CSRF. Acceptable on localhost; **block any public exposure** until upgraded.
- 2026-05-08 [sprint 1.2] **low-medium** — FastAPI container runs as root; exported files land as `root:root` on the host. `app/Dockerfile`. Fix in 1.3 with non-root user.
- 2026-05-08 [sprint 1.2] **low** — HN candidates default to `vertical=AI tools` and `production_format=cheat sheet PDF` regardless of content. `app/main.py:_hn_to_candidate`. Replace with LLM classifier in 2.1.
- 2026-05-08 [sprint 1.2] **medium** — No backups. A `docker volume rm` would erase Postgres state. Fix in 2.0.
- 2026-05-08 [sprint 1.2] **low** — Kill switch only blocks HN collect and artifact export. Mock scan, manual revenue, product edit are not gated. Widen in 1.3 if doing so does not break verification scripts.
- 2026-05-08 [sprint 1.2] **low** — No structured logging; only stdout prints. Add `structlog` in 2.x.
- 2026-05-08 [sprint 1.2] **low** — No automated tests beyond `scripts/verify_*.sh`. Add pytest harness in 2.x.
