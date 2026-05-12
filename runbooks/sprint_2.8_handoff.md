# Sprint 2.8 Handoff - Visual Layout Safety Engine

## Summary

Sprint 2.8 added deterministic layout safety validation for HYDRA marketplace
SVG assets. Product 43 covers and marketplace variants are regenerated from
named layout zones and checked for collisions, bounds issues, safe-zone issues,
and spacing problems.

## What Changed

- Added `Rect` bounding boxes and overlap detection in `app/kit_covers.py`.
- Refactored marketplace visual layout around explicit constants:
  canvas size, safe margin, left column, right visual zone, card grid, gutters,
  title/subtitle zones, bottom panel, and footer chip.
- Added layout safety report generation:
  - `products/product_43/quality/layout_safety_report.json`
  - `products/product_43/quality/layout_safety_report.md`
- Updated variant index to show `Layout PASS` per theme.
- Extended AESTHETICA to consume layout safety and block launch readiness if
  layout safety fails.
- Added `scripts/verify_sprint28.sh`.

## Product 43 Result

- Layout safety status: PASS
- Navy Gold status: PASS
- Collision count: 0
- AESTHETICA layout blocker: false

## Commands

```bash
cd /home/jb/dev/hydra
python3 scripts/build_product43_kit.py --covers-only
bash scripts/verify_sprint28.sh
LIVE=1 bash scripts/verify_sprint28.sh
bash scripts/verify_sprint26.sh
bash scripts/verify_sprint25.sh
```

## Known Gaps

- Layout safety is geometry-based, not pixel-render screenshot comparison.
- SVG assets still need manual PNG/JPG export for marketplace upload.
- Visual taste still needs final operator review before listing.

## Rollback

Revert changes to `app/kit_covers.py`, `app/aesthetica.py`, and
`scripts/verify_sprint28.sh`, then regenerate covers from the previous
generator.

## Next Recommendation

Export the Navy Gold marketplace assets to PNG/JPG and assemble the first live
Gumroad/Fiverr listing test.
