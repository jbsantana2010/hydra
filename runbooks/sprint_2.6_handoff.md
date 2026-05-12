# Sprint 2.6 Handoff - AESTHETICA Designer Agent + Hermes Foundation

## Summary

Sprint 2.6 added HYDRA's first internal specialized agent standard:
AESTHETICA, a deterministic visual/commercial design critic for marketplace
assets.

This sprint did not install Hermes or add autonomous execution. HYDRA remains
the system of record.

## Files Added

- `agents/README.md`
- `agents/AESTHETICA.md`
- `agents/HERMES_FOUNDATION.md`
- `agents/agent_registry.json`
- `app/aesthetica.py`
- `scripts/verify_sprint26.sh`
- `runbooks/sprint_2.6_handoff.md`

## Files Modified

- `app/main.py`
- `app/templates/product_edit.html`
- `runbooks/ROADMAP.md`
- `runbooks/verification_results.md`
- `runbooks/commands_run.md`
- `runbooks/known_issues.md`
- `logs/sprints/sprint_history.md`

## What AESTHETICA Does

- Reviews Product 43 marketplace visual variants.
- Scores spacing/collision risk, headline clarity, thumbnail readability,
  hierarchy, contrast, buyer outcome clarity, marketplace fit, premium feel,
  and visual density.
- Recommends the best Gumroad and Fiverr themes.
- Writes human-readable and Hermes-ready output.

## Output Files

- `products/product_43/quality/aesthetica_review.json`
- `products/product_43/quality/aesthetica_review.md`
- `products/product_43/agent_reviews/aesthetica/latest.json`

## UI

Product edit pages now include:

- `Run AESTHETICA Review`
- latest score
- best Gumroad theme
- best Fiverr theme
- strongest headline
- weakest visual issue
- Hermes output path

## Commands

```bash
cd /home/jb/dev/hydra
bash scripts/verify_sprint26.sh
LIVE=1 bash scripts/verify_sprint26.sh
bash scripts/verify_sprint25.sh
```

## Known Gaps

- AESTHETICA is deterministic and file-structure based. It does not yet do
  pixel-level visual inspection.
- SVGs still need manual export to PNG/JPG for marketplace upload.
- Hermes runtime is not installed or integrated.

## Next Recommendation

Move toward first revenue by exporting the recommended cover assets, creating
the first Gumroad/Fiverr listings manually, and adding a lightweight operator
launch checklist around the selected visual variant.
