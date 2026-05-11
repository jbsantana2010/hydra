# Known Issues

Append-only. New entries on top with date and sprint id. Resolved entries get a `~~strikethrough~~` and `(resolved <sprint-id>)` suffix; do not delete.

Format:
```
- YYYY-MM-DD [sprint <id>] **<severity>** — <description>. <file:line | route | symptom>. <mitigation in place>.
```

Severities: `low` / `medium` / `high`.

---

- 2026-05-11 [sprint 2.3] **low** — Route-generated kit files are owned by `root` because `hydra-console` still runs as root. Mitigation: acceptable for local MVP; fix with non-root container user before public/VPS deployment.
- 2026-05-11 [sprint 2.3] **low** — Product 43 has two ZIP artifacts (`Real_Estate_AI_Mastery_Kit.zip` and `Real_Estate_AI_Mastery_Kit_Kit.zip`) from standalone and route-based builds. Mitigation: use the newest route-generated ZIP for the first listing, then clean naming in the next packaging polish sprint.
- 2026-05-10 [sprint 2.2] **medium** — ~~Current execution environment has no Docker CLI, so the app could not be rebuilt/restarted for live Sprint 2.2 route verification. Port 8000 is served by an older app that returns 404 for `/kits/43`. Mitigation: integration verified by static checks and temp venv app import; rerun `docker compose up -d --build` and `LIVE=1 bash scripts/verify_sprint22.sh` on a Docker-enabled host.~~ (resolved sprint 2.3: Docker rebuild succeeded and `LIVE=1 bash scripts/verify_sprint22.sh` passes.)
- 2026-05-10 [sprint 2.2] **low** — ~~Kit content generation uses deterministic fallback sections because HYDRA's guarded LLM client returns JSON objects while the kit generator expects a JSON array of sections. Mitigation: no direct provider calls are used; add a narrow `call_llm_json` adapter in a future sprint.~~ (resolved sprint 2.3: `kit_llm_adapter.py` returns section lists via guarded `call_llm_json`, Product 43 regenerated with `fallback_used=false`.)
- 2026-05-10 [sprint 2.2] **low** — Standalone kit builds can hit permissions in host-mounted `products/product_43` if existing files were created by the container user. Mitigation: verifier writes to `/tmp`; route-based generation should run inside the container after rebuild.
- 2026-05-10 [sprint 2.1] **low** — Readiness scoring is deterministic and file-presence based, so it can mark a package ready even when human taste/design quality still needs improvement. Mitigation: report and UI preserve human review requirement; future sprint should add content QA gates.
- 2026-05-10 [sprint 2.1] **low** — Policy/IP scan is keyword-based and can miss uncommon brands or produce false positives. Mitigation: high-risk hits block readiness; human review still required.
- 2026-05-10 [sprint 2.0] **low** — Visual theme intelligence uses deterministic keyword/theme rules and may be too coarse for unusual niches. Mitigation: generated visual files are editable briefs/specs and require human review.
- 2026-05-10 [sprint 2.0] **low** — Visual bridge creates prompts/specs/manifests only, not PNG/JPG image files. This is intentional because Sprint 2.0 forbids image generation APIs and browser automation.
- 2026-05-10 [sprint 1.9] **low** — PDF export is a lightweight text-based PDF writer, not a full HTML/CSS renderer. Mitigation: package still includes printable HTML and checklist calls for human layout review before upload.
- 2026-05-10 [sprint 1.9] **low** — Preview assets are HTML previews/specs rather than PNG/JPG marketplace images. This is intentional because Sprint 1.9 forbids image generation and browser automation. Mitigation: `presentation/mockup_cover_spec.md` and `presentation/fiverr_gig_brief.md` guide manual or outsourced mockup creation.
- 2026-05-10 [sprint 1.8] **low** — Generated package files in the host-mounted `products/` directory are owned by the container user. This mirrors existing export behavior. Mitigation: acceptable for local MVP; fix alongside a non-root container user later.
- 2026-05-10 [sprint 1.8] **low** — Printable output is HTML only; PDF conversion remains manual through browser print/export. Mitigation: README and marketplace checklist explain manual PDF/mockup review requirements.
- 2026-05-10 [sprint 1.7] **low** — Sprint 1.7 verification and manual smoke leave local research runs/items/patterns and pending-review market-intelligence opportunities in the development database. Mitigation: acceptable for local MVP testing; add cleanup mode to `scripts/verify_sprint17.sh` in a future hardening pass.
- 2026-05-10 [sprint 1.7] **medium** — Anthropic primary LLM calls returned 404 in this environment during Sprint 1.7 smoke testing. OpenAI fallback successfully handled market pattern extraction after completion budget tuning. Mitigation: verify Anthropic model/key configuration before relying on primary provider.
- 2026-05-10 [sprint 1.7] **medium** — `scripts/verify_sprint15.sh` still fails generation guard-path checks after Sprint 1.7. This was observed before the Sprint 1.7 merge and appears unrelated to marketplace intelligence. Mitigation: keep Sprint 1.7 accepted based on its own verifier and manual smoke; schedule Sprint 1.5 verifier repair or generation route audit separately.
- 2026-05-09 [sprint 1.5] **low** — Generation routes return JSON on error but redirect (303) on success. Callers that follow redirects via curl -L will land on the product edit HTML, not JSON. Verification script tests guard paths (JSON) and success via DB row count, not HTTP body.
- 2026-05-09 [sprint 1.5] **low** — QA reverse_providers uses the alternate model only if both API keys are configured. With one key, QA and generation use the same model. No crash; noted in operator UX as "same-model QA".
- 2026-05-09 [sprint 1.5] **low** — Content generation max_cost_usd=$0.012; a very long outline (8 sections × long content) could approach this ceiling for Anthropic Haiku. Mitigation: ceiling is pre-call estimated and blocked before any spend occurs.
- 2026-05-09 [sprint 1.4] **low** — LLM token and cost accounting uses conservative estimates unless provider usage metadata is returned. `app/llm.py`. Mitigation: pre-call estimates are rounded up and capped before spend.
- 2026-05-09 [sprint 1.4] **low** — Verification without API keys proves fallback/guard behavior only; a real provider smoke is conditional on `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`. `scripts/verify_sprint14.sh`. Mitigation: script automatically runs a real JSON call when keys are present.
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
