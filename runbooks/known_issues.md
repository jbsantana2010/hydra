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
- 2026-05-08 [sprint 1.3] **medium** — Duplicate rows exist in `product_files` (product 34 has two `products/test/test.zip` rows from Sprint 1.2 verification). Blocks the unique index on `(product_id, file_path)`. Resolve in Sprint 2.0 alongside Alembic with a paired dedupe migration. Mitigation in place: export auto-register does an explicit existence check before insert.
- 2026-05-08 [sprint 1.3] **low** — Title prefill still truncates to 70 chars, which can lop off useful context on long topics. Acceptable until LLM-backed prefill in Sprint 1.4.
- 2026-05-08 [sprint 1.3] **low** — `_hn_classify` is an 11-rule keyword router; novel topics fall back to `(AI tools, cheat sheet PDF)`. Replace with LLM classifier in Sprint 1.4.
- 2026-05-08 [sprint 1.3] **low** — Channel rollup groups by raw `channel_tag`. Mixed casing (`Twitter` vs `twitter`) would split rows. Mitigation: insert paths lowercase the tag; relies on operator discipline elsewhere.
