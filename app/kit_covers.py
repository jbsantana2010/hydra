"""
kit_covers.py — Deterministic SVG cover asset generator for HYDRA kit documents.
Sprint 2.2. No image API required. All geometry is computed, not random.
"""

import os
import textwrap
from pathlib import Path

# ── Color system ──────────────────────────────────────────────────────────────
KIT_COLORS = {
    "real_estate": {
        "primary":     "#1a2744",
        "accent":      "#c9a84c",
        "accent_dark": "#a8882d",
        "text_light":  "#ffffff",
        "text_muted":  "rgba(255,255,255,0.60)",
        "bar":         "#c9a84c",
    },
    "default": {
        "primary":     "#1a2744",
        "accent":      "#4f7cba",
        "accent_dark": "#3a6090",
        "text_light":  "#ffffff",
        "text_muted":  "rgba(255,255,255,0.60)",
        "bar":         "#4f7cba",
    },
}

DOCUMENT_ICONS = {
    "00": "◎",   # Quick Start
    "01": "⚙",   # Setup Guide
    "02": "✦",   # Listing Description
    "03": "◈",   # Lead Follow-Up
    "04": "◉",   # Client Onboarding
    "05": "▣",   # Social Media Engine
    "06": "◆",   # Negotiation Support
    "07": "★",   # Reputation System
    "MASTER": "◈",
}


def _wrap_text_svg(text: str, max_chars: int) -> list[str]:
    """Simple word-wrap for SVG text elements."""
    words = text.split()
    lines, current = [], []
    for word in words:
        if sum(len(w) + 1 for w in current) + len(word) > max_chars:
            if current:
                lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def generate_document_cover_svg(
    doc_number: str,
    doc_title: str,
    doc_subtitle: str,
    kit_name: str,
    kit_edition: str = "2026 Edition",
    theme: str = "real_estate",
    width: int = 816,   # Letter width at 96dpi
    height: int = 1056, # Letter height at 96dpi
) -> str:
    """Generate a professional SVG cover for a single kit document."""
    c = KIT_COLORS.get(theme, KIT_COLORS["default"])
    icon = DOCUMENT_ICONS.get(doc_number, "◆")

    title_lines  = _wrap_text_svg(doc_title, 22)
    sub_lines    = _wrap_text_svg(doc_subtitle, 38)

    # Title block starting Y
    title_y_start = 340
    title_line_h  = 62
    sub_y_start   = title_y_start + len(title_lines) * title_line_h + 28

    title_svg = ""
    for i, line in enumerate(title_lines):
        title_svg += f'''    <text x="72" y="{title_y_start + i * title_line_h}"
          font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
          font-size="48" font-weight="700" fill="{c['text_light']}"
          letter-spacing="-0.5">{line}</text>\n'''

    sub_svg = ""
    for i, line in enumerate(sub_lines):
        sub_svg += f'''    <text x="72" y="{sub_y_start + i * 32}"
          font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
          font-size="20" font-weight="400" fill="{c['text_muted']}">{line}</text>\n'''

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
  width="{width}" height="{height}" viewBox="0 0 {width} {height}">

  <!-- Background -->
  <rect width="{width}" height="{height}" fill="{c['primary']}"/>

  <!-- Geometric accent shapes -->
  <rect x="{width - 320}" y="0" width="320" height="{height}"
        fill="rgba(255,255,255,0.025)"/>
  <rect x="{width - 180}" y="0" width="180" height="{height}"
        fill="rgba(255,255,255,0.02)"/>
  <circle cx="{width - 60}" cy="220" r="280"
          fill="none" stroke="{c['accent']}" stroke-width="1"
          opacity="0.20"/>
  <circle cx="{width - 60}" cy="220" r="180"
          fill="none" stroke="{c['accent']}" stroke-width="1"
          opacity="0.12"/>

  <!-- Top accent bar -->
  <rect x="0" y="0" width="{width}" height="8" fill="{c['bar']}"/>

  <!-- Kit label -->
  <text x="72" y="64"
        font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
        font-size="11" font-weight="700" fill="{c['accent']}"
        letter-spacing="2">{kit_name.upper()}  ·  {kit_edition.upper()}</text>

  <!-- Large document number watermark -->
  <text x="64" y="310"
        font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
        font-size="200" font-weight="800" fill="rgba(255,255,255,0.04)"
        letter-spacing="-6">{doc_number}</text>

  <!-- Icon -->
  <text x="72" y="230"
        font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
        font-size="48" fill="{c['accent']}" opacity="0.90">{icon}</text>

  <!-- Title lines -->
{title_svg}
  <!-- Divider -->
  <rect x="72" y="{sub_y_start - 18}" width="64" height="4" fill="{c['accent']}" rx="2"/>

  <!-- Subtitle lines -->
{sub_svg}
  <!-- Footer bar -->
  <rect x="0" y="{height - 80}" width="{width}" height="80"
        fill="rgba(0,0,0,0.25)"/>
  <text x="72" y="{height - 44}"
        font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
        font-size="11" font-weight="700" fill="rgba(255,255,255,0.30)"
        letter-spacing="3">HYDRA</text>
  <text x="{width - 72}" y="{height - 44}"
        font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
        font-size="11" font-weight="500" fill="rgba(255,255,255,0.25)"
        text-anchor="end">Document {doc_number} of 08</text>

</svg>'''
    return svg


def generate_master_cover_svg(
    kit_name: str,
    kit_tagline: str,
    kit_edition: str = "2026 Edition",
    doc_count: int = 8,
    theme: str = "real_estate",
    width: int = 816,
    height: int = 1056,
) -> str:
    """Generate the MASTER kit cover SVG."""
    c = KIT_COLORS.get(theme, KIT_COLORS["default"])
    name_lines = _wrap_text_svg(kit_name, 20)
    tag_lines  = _wrap_text_svg(kit_tagline, 40)

    name_y = 360
    name_h = 66
    tag_y  = name_y + len(name_lines) * name_h + 32

    name_svg = ""
    for i, line in enumerate(name_lines):
        name_svg += f'''    <text x="72" y="{name_y + i * name_h}"
          font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
          font-size="52" font-weight="800" fill="{c['text_light']}"
          letter-spacing="-0.5">{line}</text>\n'''

    tag_svg = ""
    for i, line in enumerate(tag_lines):
        tag_svg += f'''    <text x="72" y="{tag_y + i * 34}"
          font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
          font-size="21" font-weight="400" fill="{c['text_muted']}">{line}</text>\n'''

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
  width="{width}" height="{height}" viewBox="0 0 {width} {height}">

  <rect width="{width}" height="{height}" fill="{c['primary']}"/>

  <!-- Diagonal accent geometry -->
  <polygon points="{width},0 {width},{height} {width-400},{height}"
           fill="rgba(255,255,255,0.03)"/>
  <polygon points="{width},0 {width},{int(height*0.6)} {width-220},{int(height*0.3)}"
           fill="rgba(255,255,255,0.03)"/>

  <!-- Concentric rings -->
  <circle cx="{width + 40}" cy="{int(height * 0.35)}" r="420"
          fill="none" stroke="{c['accent']}" stroke-width="1.5" opacity="0.18"/>
  <circle cx="{width + 40}" cy="{int(height * 0.35)}" r="280"
          fill="none" stroke="{c['accent']}" stroke-width="1"   opacity="0.12"/>
  <circle cx="{width + 40}" cy="{int(height * 0.35)}" r="160"
          fill="none" stroke="{c['accent']}" stroke-width="1"   opacity="0.08"/>

  <!-- Top accent bar (thicker for master) -->
  <rect x="0" y="0" width="{width}" height="12" fill="{c['bar']}"/>

  <!-- COMPLETE KIT label -->
  <text x="72" y="70"
        font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
        font-size="10" font-weight="700" fill="{c['accent']}"
        letter-spacing="3">COMPLETE KIT  ·  {doc_count} DOCUMENTS  ·  {kit_edition.upper()}</text>

  <!-- Watermark star -->
  <text x="60" y="290"
        font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
        font-size="160" fill="rgba(255,255,255,0.04)" font-weight="800">◈</text>

  <!-- Kit name -->
{name_svg}
  <!-- Gold divider -->
  <rect x="72" y="{tag_y - 22}" width="80" height="5" fill="{c['accent']}" rx="2.5"/>

  <!-- Tagline -->
{tag_svg}
  <!-- Document list strip -->
  <rect x="0" y="{height - 200}" width="{width}" height="200"
        fill="rgba(0,0,0,0.30)"/>
  <text x="72" y="{height - 160}"
        font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
        font-size="9" font-weight="700" fill="{c['accent']}"
        letter-spacing="2.5">INCLUDED IN THIS KIT</text>

  <text x="72" y="{height - 134}"
        font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
        font-size="9.5" fill="rgba(255,255,255,0.50)">
    Quick Start Guide  ·  AI Tools Setup  ·  Listing Description System  ·  Lead Follow-Up Pack
  </text>
  <text x="72" y="{height - 112}"
        font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
        font-size="9.5" fill="rgba(255,255,255,0.50)">
    Client Onboarding System  ·  Social Media Engine  ·  Negotiation Support  ·  Reputation System
  </text>

  <text x="72" y="{height - 44}"
        font-family="system-ui,-apple-system,Segoe UI,Helvetica,sans-serif"
        font-size="11" font-weight="700" fill="rgba(255,255,255,0.28)"
        letter-spacing="3">HYDRA</text>

</svg>'''
    return svg


def build_kit_covers(
    product_dir: str | Path,
    kit_name: str,
    kit_tagline: str,
    kit_edition: str = "2026 Edition",
    theme: str = "real_estate",
) -> dict[str, str]:
    """
    Generate all SVG covers for a kit and write them to product_dir/covers/.
    Returns a dict mapping filename → absolute path.
    """
    covers_dir = Path(product_dir) / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)

    documents = [
        ("00", "Quick Start Guide",          "Get your first result in 30 minutes"),
        ("01", "AI Tools Setup Guide",        "Zero friction setup for ChatGPT and Claude"),
        ("02", "Listing Description System",  "Write compelling listings in under 10 minutes"),
        ("03", "Lead Follow-Up Pack",         "18 ready-to-send messages for every stage"),
        ("04", "Client Onboarding System",    "Make every first meeting structured and professional"),
        ("05", "Social Media Content Engine", "30-day content system for consistent visibility"),
        ("06", "Negotiation Support Pack",    "Language and frameworks for high-stakes moments"),
        ("07", "Reputation & Review System",  "Systematize reviews and referrals after every close"),
    ]

    paths = {}

    for num, title, subtitle in documents:
        svg = generate_document_cover_svg(
            doc_number=num,
            doc_title=title,
            doc_subtitle=subtitle,
            kit_name=kit_name,
            kit_edition=kit_edition,
            theme=theme,
        )
        fname = f"cover_{num}.svg"
        fpath = covers_dir / fname
        fpath.write_text(svg, encoding="utf-8")
        paths[fname] = str(fpath)

    # Master cover
    master_svg = generate_master_cover_svg(
        kit_name=kit_name,
        kit_tagline=kit_tagline,
        kit_edition=kit_edition,
        doc_count=len(documents),
        theme=theme,
    )
    master_path = covers_dir / "cover_MASTER.svg"
    master_path.write_text(master_svg, encoding="utf-8")
    paths["cover_MASTER.svg"] = str(master_path)

    return paths


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/hydra_covers_test"
    result = build_kit_covers(
        product_dir=out,
        kit_name="Real Estate AI Mastery Kit",
        kit_tagline="The complete AI implementation system for modern agents",
    )
    for fname, path in result.items():
        print(f"  ✓ {fname}  →  {path}")
    print(f"\n{len(result)} covers written to {out}/covers/")
