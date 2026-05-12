from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import cairosvg

from kit_covers import generate_refined_gumroad_cover_svg


PRODUCT_NAME = "Real Estate AI Mastery Kit"
SELECTED_STYLE = "minimal_enterprise"


def export_product_43_marketplace_assets(product_dir: str | Path = "products/product_43") -> dict:
    product_path = Path(product_dir)
    visuals_dir = product_path / "marketplace_visuals"
    final_dir = product_path / "final_assets"
    archive_dir = product_path / "archive"
    gumroad_dir = final_dir / "gumroad"
    fiverr_dir = final_dir / "fiverr"
    source_dir = final_dir / "archive"
    for path in (gumroad_dir, fiverr_dir, source_dir, archive_dir):
        path.mkdir(parents=True, exist_ok=True)

    selected_svg = visuals_dir / "refined" / SELECTED_STYLE / "gumroad_cover.svg"
    if not selected_svg.exists():
        selected_svg.parent.mkdir(parents=True, exist_ok=True)
        selected_svg.write_text(generate_refined_gumroad_cover_svg(SELECTED_STYLE), encoding="utf-8")

    square_svg = source_dir / "gumroad_thumbnail_square.svg"
    square_svg.write_text(generate_square_thumbnail_svg(), encoding="utf-8")

    source_map = {
        source_dir / "hero_cover.svg": selected_svg,
        source_dir / "value_stack.svg": visuals_dir / "value_stack.svg",
        source_dir / "included_documents.svg": visuals_dir / "eight_documents_included.svg",
        source_dir / "product_mockup.svg": visuals_dir / "product_mockup.svg",
        source_dir / "fiverr_main_1280x769.svg": visuals_dir / "fiverr_gig_image_1280x769.svg",
    }
    for dest, src in source_map.items():
        if src.exists():
            shutil.copy2(src, dest)

    exports = [
        (square_svg, gumroad_dir / "thumbnail_square.png", 1200, 1200),
        (selected_svg, gumroad_dir / "hero_cover.png", 1600, 900),
        (visuals_dir / "value_stack.svg", gumroad_dir / "value_stack.png", 1280, 769),
        (visuals_dir / "eight_documents_included.svg", gumroad_dir / "included_documents.png", 1280, 769),
        (visuals_dir / "product_mockup.svg", gumroad_dir / "product_mockup.png", 1280, 769),
        (visuals_dir / "fiverr_gig_image_1280x769.svg", fiverr_dir / "fiverr_main_1280x769.png", 1280, 769),
        (selected_svg, fiverr_dir / "fiverr_secondary.png", 1280, 720),
    ]
    written = []
    for src, dest, width, height in exports:
        if not src.exists():
            raise FileNotFoundError(f"Missing source SVG: {src}")
        export_svg_to_png(src, dest, width, height)
        written.append({"path": str(dest), "width": width, "height": height})

    _archive_obsolete_visuals(visuals_dir, archive_dir)
    manifest_path = final_dir / "ASSET_MANIFEST.md"
    manifest_path.write_text(_asset_manifest(written), encoding="utf-8")
    return {
        "final_assets": str(final_dir),
        "exports": written,
        "manifest": str(manifest_path),
        "selected_style": SELECTED_STYLE,
    }


def export_svg_to_png(svg_path: str | Path, output_path: str | Path, width: int, height: int) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(output),
        output_width=width,
        output_height=height,
    )


def generate_square_thumbnail_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="0 0 1200 1200">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#14213d"/>
      <stop offset="100%" stop-color="#253660"/>
    </linearGradient>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#c9a84c"/>
      <stop offset="100%" stop-color="#e7c96c"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="18" stdDeviation="18" flood-color="#000000" flood-opacity="0.22"/>
    </filter>
  </defs>
  <rect width="1200" height="1200" fill="url(#bg)"/>
  <rect x="92" y="92" width="1016" height="1016" rx="42" fill="#ffffff" opacity="0.055" stroke="#ffffff" stroke-opacity="0.13"/>
  <text x="132" y="178" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="24" font-weight="850" fill="#c9a84c" letter-spacing="4">PREMIUM BUSINESS KIT</text>
  <text x="132" y="356" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="92" font-weight="920" fill="#ffffff">Real Estate</text>
  <text x="132" y="462" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="92" font-weight="920" fill="#ffffff">AI Mastery</text>
  <text x="132" y="568" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="92" font-weight="920" fill="#ffffff">Kit</text>
  <rect x="132" y="626" width="118" height="7" rx="4" fill="url(#gold)"/>
  <text x="132" y="704" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="32" font-weight="560" fill="#ffffff" opacity="0.82">AI workflows for listings,</text>
  <text x="132" y="748" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="32" font-weight="560" fill="#ffffff" opacity="0.82">follow-up, and reviews.</text>
  <g transform="translate(790 674) rotate(-6)" opacity="0.58">
    <rect x="0" y="0" width="188" height="242" rx="16" fill="#ffffff" filter="url(#shadow)"/>
    <rect x="0" y="0" width="188" height="15" rx="8" fill="#c9a84c"/>
    <line x1="28" y1="74" x2="156" y2="74" stroke="#253660" opacity="0.22"/>
    <line x1="28" y1="112" x2="142" y2="112" stroke="#253660" opacity="0.18"/>
    <rect x="-48" y="42" width="188" height="242" rx="16" fill="#ffffff" opacity="0.78" filter="url(#shadow)"/>
    <rect x="-48" y="42" width="188" height="15" rx="8" fill="#c9a84c"/>
    <line x1="-20" y1="116" x2="108" y2="116" stroke="#253660" opacity="0.20"/>
    <line x1="-20" y1="154" x2="94" y2="154" stroke="#253660" opacity="0.16"/>
  </g>
  <rect x="132" y="944" width="438" height="92" rx="24" fill="#f7f3e8" opacity="0.95"/>
  <text x="166" y="1000" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="24" font-weight="780" fill="#14213d">8-document implementation system</text>
  <text x="132" y="1084" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="17" font-weight="900" fill="#c9a84c" letter-spacing="4">HYDRA</text>
</svg>"""


def _archive_obsolete_visuals(visuals_dir: Path, archive_dir: Path) -> None:
    archive_visuals = archive_dir / "marketplace_visuals_obsolete"
    archive_visuals.mkdir(parents=True, exist_ok=True)
    for name in ("variants",):
        src = visuals_dir / name
        if src.exists():
            dest = archive_visuals / name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(src), str(dest))


def _asset_manifest(exports: list[dict]) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    rows = "\n".join(
        f"| `{Path(item['path']).relative_to('products/product_43/final_assets')}` | {item['width']}x{item['height']} |"
        for item in exports
    )
    return f"""# Product 43 Final Asset Manifest

Generated: {generated}

Selected visual direction: **minimal_enterprise**

## Gumroad Upload Order

1. `gumroad/thumbnail_square.png` — primary thumbnail, 1200x1200
2. `gumroad/hero_cover.png` — product hero/gallery image, 1600x900
3. `gumroad/value_stack.png` — secondary gallery image
4. `gumroad/included_documents.png` — included documents image
5. `gumroad/product_mockup.png` — product mockup image

## Fiverr Upload Order

1. `fiverr/fiverr_main_1280x769.png` — main gig image
2. `fiverr/fiverr_secondary.png` — supporting premium cover image

## Exported PNGs

| File | Dimensions |
|---|---:|
{rows}

## Source SVG Archive

Curated source SVGs are stored in `final_assets/archive/`.
Obsolete experimental variants were moved to `products/product_43/archive/`.

## Operator Note

Use these PNG files directly. No screenshots are required.
"""


if __name__ == "__main__":
    print(export_product_43_marketplace_assets())
