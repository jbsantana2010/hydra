# Sprint 2.9 Handoff - Production Marketplace Exports

## Summary

Sprint 2.9 turns Product 43 marketplace visuals into launch-ready PNG assets.
The operator no longer needs screenshots.

## Final Asset Folder

`products/product_43/final_assets/`

Gumroad:

- `gumroad/thumbnail_square.png`
- `gumroad/hero_cover.png`
- `gumroad/value_stack.png`
- `gumroad/included_documents.png`
- `gumroad/product_mockup.png`

Fiverr:

- `fiverr/fiverr_main_1280x769.png`
- `fiverr/fiverr_secondary.png`

Sources:

- `final_assets/archive/` contains curated source SVGs only.
- old palette variants moved to `products/product_43/archive/marketplace_visuals_obsolete/variants/`.

## Export Pipeline

`app/marketplace_export.py` uses CairoSVG for deterministic SVG-to-PNG export.
No screenshots or browser automation are required.

## Selected Direction

Selected visual direction: `minimal_enterprise`.

## Verification

```bash
cd /home/jb/dev/hydra
bash scripts/verify_sprint29.sh
bash scripts/verify_sprint282.sh
```

## Remaining Launch Work

- Upload final PNGs to Gumroad/Fiverr manually.
- Confirm final listing copy and pricing.
- Run one operator visual pass on the exported PNGs.
