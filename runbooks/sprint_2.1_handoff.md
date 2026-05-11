# Sprint 2.1 Handoff — Package Quality Scoring + Upload Readiness

Date: 2026-05-10  
Executor: Codex  
Source of truth: `/home/jb/dev/hydra`

## Implementation Summary

Sprint 2.1 adds deterministic upload-readiness scoring for packaged products. HYDRA now generates a quality report after packaging and tells the operator whether a package is ready to sell.

No marketplace publishing, image generation, scraping, Celery, scheduler, browser automation, React rewrite, or LLM scoring was added.

## Files Changed

- `app/main.py`
- `app/templates/product_edit.html`
- `scripts/verify_sprint21.sh`
- `runbooks/sprint_2.1_handoff.md`
- `runbooks/ROADMAP.md`
- `runbooks/verification_results.md`
- `runbooks/commands_run.md`
- `runbooks/known_issues.md`
- `logs/sprints/sprint_history.md`

## New Route

```http
POST /products/{id}/quality-check
```

The route writes quality reports under:

```text
products/product_<id>/quality/
```

## Generated Quality Files

- `readiness_report.json`
- `readiness_report.md`
- `platform_readiness.md`
- `missing_assets.md`
- `policy_risk_check.md`
- `improvement_plan.md`

## Scoring

Deterministic score out of 100:

- required files present: 25
- source markdown present: 10
- printable files present: 10
- PDF present: 10
- listing copy present: 10
- preview assets present: 10
- visual specs present: 10
- marketplace checklist present: 5
- policy risk clean: 5
- package ZIP present: 5

Ready threshold: `80+`, unless a hard blocker exists.

Hard blockers:

- no package ZIP
- missing listing_copy
- missing product_content
- no README
- no manifest
- no marketplace checklist
- high policy/IP risk keyword found

## Product 43 Result

- Readiness score: `100`
- Readiness status: `ready`
- Blockers: none
- Policy/IP risk: low
- Platform readiness: Gumroad, Fiverr, Payhip, Sellfy, and Pinterest are all ready by deterministic checks.

## Commands Run

```bash
cd /home/jb/dev/hydra
./scripts/preflight_check.sh
bash scripts/verify_sprint21.sh
docker compose up -d --build
LIVE=1 bash scripts/verify_sprint21.sh
bash scripts/verify_sprint20.sh
LIVE=1 bash scripts/verify_sprint20.sh
find products/product_43/quality -maxdepth 1 -type f | sort
python3 -m json.tool products/product_43/quality/readiness_report.json
```

## Verification Results

- `./scripts/preflight_check.sh`: PASS
- `bash scripts/verify_sprint21.sh`: PASS, 13/13
- `LIVE=1 bash scripts/verify_sprint21.sh`: PASS, 25/25
- `bash scripts/verify_sprint20.sh`: PASS, 13/13
- `LIVE=1 bash scripts/verify_sprint20.sh`: PASS, 26/26

## Manual Smoke

Product 43 was packaged, then quality-checked through the live route.

Verified:

- `products/product_43/quality/readiness_report.json`
- `products/product_43/quality/readiness_report.md`
- `products/product_43/quality/platform_readiness.md`
- `products/product_43/quality/missing_assets.md`
- `products/product_43/quality/policy_risk_check.md`
- `products/product_43/quality/improvement_plan.md`
- Product edit page renders the readiness section and score.
- Manifest includes `quality_report`, `readiness_status`, and `readiness_score`.

## Known Issues

- Scoring is deterministic and file-presence based; it does not judge visual beauty, copy quality, or real marketplace conversion.
- Policy/IP risk scan is keyword-based and may miss uncommon brands or false-positive generic terms.
- Product 43 scores 100 because all deterministic assets are present; human review is still required before publishing.

## Rollback Notes

```bash
cd /home/jb/dev/hydra
git checkout -- app/main.py app/templates/product_edit.html scripts/verify_sprint21.sh
rm -rf products/product_<id>/quality
```

If the manifest should also be reverted for a generated package, rebuild the package with the previous code or remove `quality_report`, `readiness_status`, and `readiness_score` manually.

## Next Sprint Recommendation

Sprint 2.2 should add deterministic package QA gates for content quality and marketplace policy review: spelling/placeholder checks, empty-section checks, overclaim detection, license consistency, and upload checklist signoff.
