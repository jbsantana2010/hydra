# Sprint 1.8 Handoff — Product Asset Generator v1

Date: 2026-05-10  
Executor: Codex  
Source of truth: `/home/jb/dev/hydra`

## Implementation Summary

Sprint 1.8 adds local product asset generation and packaging. HYDRA can now turn approved/generated product artifacts into a marketplace-ready local ZIP package with Markdown source files, printable HTML files for printable-style products, README, manifest, and marketplace upload checklist.

No marketplace publishing, external APIs, scraping, image generation, scheduler, or automation beyond local file packaging was added.

## Files Changed

- `app/main.py`
- `app/templates/product_edit.html`
- `docker-compose.yml`
- `scripts/verify_sprint18.sh`
- `runbooks/ROADMAP.md`
- `runbooks/sprint_1.8_handoff.md`
- `runbooks/verification_results.md`
- `runbooks/commands_run.md`
- `runbooks/known_issues.md`
- `logs/sprints/sprint_history.md`

Generated local package files are written under `products/`, which is host-mounted into the app container and ignored by git.

## Behavior

`POST /products/{id}/package`:

- Requires latest `outline`, `product_content`, and `listing_copy` artifacts.
- Writes `products/product_<id>/source/*.md`.
- Writes `products/product_<id>/printable/*.html` for planner/printable/worksheet/tracker/checklist formats.
- Writes `README.md`.
- Writes `manifest.json`.
- Writes `marketplace_checklist.md`.
- Builds `products/product_<id>.zip`.
- Registers the ZIP in `product_files` with `file_type='package_zip'`.

Missing required artifacts redirect back to product edit with a clear message such as `Missing required artifact: product_content`.

## Commands Run

```bash
cd /home/jb/dev/hydra
git status
git log --oneline -10
./scripts/preflight_check.sh
bash scripts/verify_sprint17.sh
LIVE=1 bash scripts/verify_sprint17.sh
python3 -m py_compile app/main.py app/db.py app/llm.py
chmod +x scripts/verify_sprint18.sh
bash scripts/verify_sprint18.sh
docker compose up -d --build
./scripts/preflight_check.sh
LIVE=1 bash scripts/verify_sprint18.sh
curl -u admin:change-me -X POST http://localhost:8000/products/43/package
```

## Verification Results

- `./scripts/preflight_check.sh`: PASS
- `bash scripts/verify_sprint17.sh`: PASS
- `LIVE=1 bash scripts/verify_sprint17.sh`: PASS
- `python3 -m py_compile app/main.py app/db.py app/llm.py`: PASS
- `bash scripts/verify_sprint18.sh`: PASS, 7/7
- `LIVE=1 bash scripts/verify_sprint18.sh`: PASS, 17/17

## Manual UI Smoke

Product 43 was packaged through the route used by the UI button:

```bash
curl -u admin:change-me -X POST http://localhost:8000/products/43/package
```

Verified outputs:

- `products/product_43.zip`
- `products/product_43/README.md`
- `products/product_43/manifest.json`
- `products/product_43/marketplace_checklist.md`
- `products/product_43/source/outline.md`
- `products/product_43/source/product_content.md`
- `products/product_43/source/listing_copy.md`
- `products/product_43/source/qa_review.md`
- `products/product_43/source/distribution_post.md`
- `products/product_43/printable/*.html`
- `product_files` has a `package_zip` row for product 43.

## Known Issues

- Generated files are owned by the container user in the host-mounted `products/` directory. This matches the existing exports behavior and is acceptable for local MVP use.
- Printable HTML is intentionally plain and browser-printable. PDF conversion is not automated in this sprint.
- Image/mockup creation is still manual and is explicitly called out in the marketplace checklist.

## Rollback Notes

To roll back code changes:

```bash
cd /home/jb/dev/hydra
git checkout -- app/main.py app/templates/product_edit.html docker-compose.yml scripts/verify_sprint18.sh
```

To remove generated local packages:

```bash
rm -rf products/product_<id> products/product_<id>.zip
```

`product_files` rows created by packaging can be left as historical records or deleted manually if cleaning the dev database.

## Next Sprint Recommendation

Sprint 1.9 should improve product file quality and marketplace readiness: optional PDF conversion when available, better printable templates by product type, and a manual mockup/image checklist workflow without adding image generation or marketplace publishing.
