"""
kit_covers.py — deterministic SVG cover and marketplace visual generator.

Sprint 2.5 refines marketplace layouts with explicit spacing constants and
palette variants. No image APIs. No browser automation.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PALETTES = {
    "navy_gold": {
        "name": "Navy Gold",
        "use_case": "Premium consulting default. Best first-listing candidate.",
        "primary": "#14213d",
        "primary_2": "#1a2744",
        "primary_3": "#253660",
        "accent": "#c9a84c",
        "accent_2": "#e7c96c",
        "cream": "#f7f3e8",
        "paper": "#ffffff",
        "muted": "#9aa7bd",
        "ink": "#111827",
        "text_light": "#ffffff",
        "panel": "#08111f",
        "shadow": "#000000",
    },
    "charcoal_emerald": {
        "name": "Charcoal Emerald",
        "use_case": "Modern high-trust operations/SaaS feel.",
        "primary": "#111827",
        "primary_2": "#1f2937",
        "primary_3": "#374151",
        "accent": "#10b981",
        "accent_2": "#6ee7b7",
        "cream": "#ecfdf5",
        "paper": "#ffffff",
        "muted": "#a7f3d0",
        "ink": "#0f172a",
        "text_light": "#ffffff",
        "panel": "#07111f",
        "shadow": "#000000",
    },
    "white_navy_gold": {
        "name": "White Navy Gold",
        "use_case": "Bright marketplace thumbnail, clean executive style.",
        "primary": "#f8fafc",
        "primary_2": "#eef2f7",
        "primary_3": "#dbe4ef",
        "accent": "#c9a84c",
        "accent_2": "#8d6f24",
        "cream": "#ffffff",
        "paper": "#ffffff",
        "muted": "#475569",
        "ink": "#0f172a",
        "text_light": "#0f172a",
        "panel": "#ffffff",
        "shadow": "#64748b",
    },
    "deep_teal_copper": {
        "name": "Deep Teal Copper",
        "use_case": "Luxury real estate and boutique agent positioning.",
        "primary": "#0f2f35",
        "primary_2": "#16434a",
        "primary_3": "#235d63",
        "accent": "#c47a4a",
        "accent_2": "#f0b487",
        "cream": "#f8eee7",
        "paper": "#ffffff",
        "muted": "#a7d5d6",
        "ink": "#102a2f",
        "text_light": "#ffffff",
        "panel": "#071b1f",
        "shadow": "#000000",
    },
    "black_platinum_blue": {
        "name": "Black Platinum Blue",
        "use_case": "AI/high-tech premium product positioning.",
        "primary": "#05070d",
        "primary_2": "#111827",
        "primary_3": "#1e3a5f",
        "accent": "#8fb7ff",
        "accent_2": "#d8e6ff",
        "cream": "#eef4ff",
        "paper": "#ffffff",
        "muted": "#a6b8d6",
        "ink": "#0b1020",
        "text_light": "#ffffff",
        "panel": "#070b14",
        "shadow": "#000000",
    },
}

KIT_COLORS = {
    "real_estate": PALETTES["navy_gold"],
    "default": PALETTES["navy_gold"],
    **PALETTES,
}

DOCUMENTS = [
    ("00", "Quick Start Guide", "Get your first result in 30 minutes", "Start"),
    ("01", "AI Tools Setup Guide", "Zero friction setup for ChatGPT and Claude", "Setup"),
    ("02", "Listing Description System", "Write compelling listings in under 10 minutes", "Listings"),
    ("03", "Lead Follow-Up Pack", "18 ready-to-send messages for every stage", "Follow-Up"),
    ("04", "Client Onboarding System", "Make every first meeting structured and professional", "Onboarding"),
    ("05", "Social Media Content Engine", "30-day content system for consistent visibility", "Content"),
    ("06", "Negotiation Support Pack", "Language and frameworks for high-stakes moments", "Negotiation"),
    ("07", "Reputation & Review System", "Systematize reviews and referrals after every close", "Reviews"),
]

HEADLINE_VARIANTS = {
    "gumroad_cover": (
        "Real Estate AI Mastery Kit",
        "Close More Deals in Less Time With AI",
    ),
    "fiverr_gig_image": (
        "AI Systems for Real Estate Agents",
        "Listings, Follow-Ups, Content & Client Workflows in Minutes",
    ),
    "value_stack": (
        "The Real Estate Agent AI Toolkit",
        "40+ Prompts, Workflows & Scripts for Modern Agents",
    ),
    "included": (
        "Turn AI Into Your Real Estate Assistant",
        "Client-ready systems for listings, follow-up, content, and reviews",
    ),
    "mockup": (
        "Premium Real Estate AI Toolkit",
        "A polished operating system for faster listings and better follow-up",
    ),
    "payhip_sellfy": (
        "Real Estate AI Mastery Kit",
        "Practical AI workflows for agents who want to stay ahead",
    ),
}

MARKETPLACE_FILES = {
    "gumroad_cover": "gumroad_cover.svg",
    "fiverr_gig_image": "fiverr_gig_image_1280x769.svg",
    "value_stack": "value_stack.svg",
    "included": "eight_documents_included.svg",
    "mockup": "product_mockup.svg",
    "payhip_sellfy": "payhip_sellfy_cover.svg",
}
MARKETPLACE_KIND_BY_FILE = {filename: kind for kind, filename in MARKETPLACE_FILES.items()}


@dataclass(frozen=True)
class Rect:
    name: str
    x: int
    y: int
    width: int
    height: int
    kind: str = "element"

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def intersects(self, other: "Rect", gap: int = 0) -> bool:
        return not (
            self.right + gap <= other.x
            or other.right + gap <= self.x
            or self.bottom + gap <= other.y
            or other.bottom + gap <= self.y
        )

    def inside(self, width: int, height: int, margin: int = 0) -> bool:
        return (
            self.x >= margin
            and self.y >= margin
            and self.right <= width - margin
            and self.bottom <= height - margin
        )

    def as_dict(self) -> dict[str, int | str]:
        return {
            "name": self.name,
            "kind": self.kind,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "right": self.right,
            "bottom": self.bottom,
        }


def _gap_between(a: Rect, b: Rect) -> int:
    if a.intersects(b):
        return 0
    horizontal = max(b.x - a.right, a.x - b.right, 0)
    vertical = max(b.y - a.bottom, a.y - b.bottom, 0)
    if horizontal and vertical:
        return min(horizontal, vertical)
    return horizontal or vertical


def _esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def _wrap_text_svg(text: str, max_chars: int) -> list[str]:
    words = str(text).split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        proposed = " ".join(current + [word])
        if current and len(proposed) > max_chars:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def _text_lines(lines: list[str], x: int, y: int, size: int, weight: int, fill: str, line_gap: int, anchor: str = "start") -> str:
    return "\n".join(
        f'<text x="{x}" y="{y + i * line_gap}" font-family="Inter,Segoe UI,Arial,sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{_esc(line)}</text>'
        for i, line in enumerate(lines)
    )


def _premium_background(width: int, height: int, c: dict) -> str:
    grid = "#ffffff" if c["text_light"] == "#ffffff" else c["primary_3"]
    return f"""
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c['primary']}"/>
      <stop offset="56%" stop-color="{c['primary_2']}"/>
      <stop offset="100%" stop-color="{c['primary_3']}"/>
    </linearGradient>
    <linearGradient id="accentGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{c['accent']}"/>
      <stop offset="100%" stop-color="{c['accent_2']}"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="16" stdDeviation="17" flood-color="{c['shadow']}" flood-opacity="0.24"/>
    </filter>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bg)"/>
  <path d="M{int(width*.61)} 0 L{width} 0 L{width} {height} L{int(width*.80)} {height} Z" fill="#ffffff" opacity="0.045"/>
  <path d="M0 {int(height*.76)} C{int(width*.22)} {int(height*.62)}, {int(width*.50)} {int(height*.94)}, {width} {int(height*.80)} L{width} {height} L0 {height} Z" fill="#000000" opacity="0.12"/>
  <g opacity="0.10">
    <path d="M80 130 H{width-92} M80 230 H{width-150} M80 330 H{width-112} M80 430 H{width-170}" stroke="{grid}" stroke-width="1"/>
    <path d="M160 72 V{height-136} M270 72 V{height-186} M380 72 V{height-154} M490 72 V{height-206}" stroke="{grid}" stroke-width="1"/>
  </g>
  <circle cx="{width-124}" cy="142" r="238" fill="none" stroke="{c['accent']}" stroke-width="1.2" opacity="0.20"/>
  <circle cx="{width-124}" cy="142" r="138" fill="none" stroke="{c['accent_2']}" stroke-width="1" opacity="0.14"/>
"""


def _mini_stack(x: int, y: int, c: dict, scale: float = 1.0) -> str:
    w = int(156 * scale)
    h = int(198 * scale)
    gap = int(16 * scale)
    docs = []
    for i in range(4):
        dx = i * gap
        dy = i * int(10 * scale)
        docs.append(
            f'<rect x="{x+dx}" y="{y+dy}" width="{w}" height="{h}" rx="{int(9*scale)}" fill="{c["paper"]}" opacity="{0.90 - i*.10}" filter="url(#shadow)"/>'
            f'<rect x="{x+dx}" y="{y+dy}" width="{w}" height="{int(11*scale)}" rx="{int(6*scale)}" fill="{c["accent"]}" opacity="0.92"/>'
            f'<line x1="{x+dx+int(22*scale)}" y1="{y+dy+int(56*scale)}" x2="{x+dx+w-int(22*scale)}" y2="{y+dy+int(56*scale)}" stroke="{c["primary_3"]}" opacity="0.22"/>'
            f'<line x1="{x+dx+int(22*scale)}" y1="{y+dy+int(83*scale)}" x2="{x+dx+w-int(42*scale)}" y2="{y+dy+int(83*scale)}" stroke="{c["primary_3"]}" opacity="0.18"/>'
        )
    return "\n".join(docs)


def generate_document_cover_svg(
    doc_number: str,
    doc_title: str,
    doc_subtitle: str,
    kit_name: str,
    kit_edition: str = "2026 Edition",
    theme: str = "real_estate",
    width: int = 816,
    height: int = 1056,
) -> str:
    c = KIT_COLORS.get(theme, KIT_COLORS["default"])
    title_lines = _wrap_text_svg(doc_title, 18)
    sub_lines = _wrap_text_svg(doc_subtitle, 34)
    title_y = 356
    sub_y = title_y + len(title_lines) * 58 + 34

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
{_premium_background(width, height, c)}
  <rect x="54" y="54" width="{width-108}" height="{height-108}" rx="26" fill="#ffffff" opacity="0.060" stroke="#ffffff" stroke-opacity="0.14"/>
  <rect x="72" y="88" width="190" height="32" rx="16" fill="{c['accent']}" opacity="0.18"/>
  <text x="92" y="110" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="11" font-weight="800" fill="{c['accent']}" letter-spacing="2">REAL ESTATE AI KIT</text>
  <text x="{width-72}" y="108" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="10" font-weight="700" fill="{c['text_light']}" opacity="0.56" text-anchor="end">{_esc(kit_edition.upper())}</text>
  <rect x="72" y="178" width="118" height="118" rx="24" fill="url(#accentGrad)" filter="url(#shadow)"/>
  <text x="131" y="250" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="35" font-weight="900" fill="{c['primary']}" text-anchor="middle">{doc_number}</text>
  <text x="212" y="223" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="10" font-weight="800" fill="{c['accent']}" letter-spacing="2">DOCUMENT {doc_number} / 08</text>
  <text x="212" y="253" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="13" font-weight="650" fill="{c['text_light']}" opacity="0.70">Implementation playbook for modern agents</text>
  <g transform="translate(466 648) rotate(-8)">{_mini_stack(0, 0, c, 1.0)}</g>
  {_text_lines(title_lines, 72, title_y, 49, 850, c["text_light"], 56)}
  <rect x="72" y="{sub_y - 20}" width="92" height="6" rx="3" fill="url(#accentGrad)"/>
  {_text_lines(sub_lines, 72, sub_y, 21, 500, c["text_light"], 31)}
  <g transform="translate(72 {height-238})">
    <rect width="{width-144}" height="120" rx="18" fill="{c['panel']}" opacity="0.68" stroke="#ffffff" stroke-opacity="0.10"/>
    <text x="26" y="34" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="9" font-weight="800" fill="{c['accent']}" letter-spacing="2">WHAT THIS UNLOCKS</text>
    <text x="26" y="66" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" font-weight="650" fill="#ffffff">Reusable workflows, prompts, checklists, and client-ready operating systems.</text>
    <text x="26" y="94" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="11" fill="rgba(255,255,255,0.62)">Built for immediate application in a real estate business.</text>
  </g>
  <rect x="0" y="{height-70}" width="{width}" height="70" fill="#050b14" opacity="0.72"/>
  <text x="72" y="{height-31}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="11" font-weight="900" fill="{c['accent']}" letter-spacing="3">HYDRA</text>
  <text x="{width-72}" y="{height-31}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="10" font-weight="700" fill="rgba(255,255,255,0.48)" text-anchor="end">{_esc(kit_name)}</text>
</svg>"""


def generate_master_cover_svg(
    kit_name: str,
    kit_tagline: str,
    kit_edition: str = "2026 Edition",
    doc_count: int = 8,
    theme: str = "real_estate",
    width: int = 816,
    height: int = 1056,
) -> str:
    c = KIT_COLORS.get(theme, KIT_COLORS["default"])
    name_lines = _wrap_text_svg(kit_name, 17)
    tag_lines = _wrap_text_svg(kit_tagline, 36)
    name_y = 318
    tag_y = name_y + len(name_lines) * 62 + 34
    doc_badges = "\n".join(
        f'<rect x="{72 + (i % 4) * 168}" y="{height - 268 + (i // 4) * 52}" width="144" height="34" rx="17" fill="#ffffff" opacity="0.09"/>'
        f'<text x="{92 + (i % 4) * 168}" y="{height - 246 + (i // 4) * 52}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="10" font-weight="800" fill="{c["accent"]}">{num}</text>'
        f'<text x="{124 + (i % 4) * 168}" y="{height - 246 + (i // 4) * 52}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="9" font-weight="650" fill="#ffffff" opacity="0.76">{_esc(short)}</text>'
        for i, (num, _title, _subtitle, short) in enumerate(DOCUMENTS)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
{_premium_background(width, height, c)}
  <rect x="42" y="42" width="{width-84}" height="{height-84}" rx="30" fill="#ffffff" opacity="0.06" stroke="#ffffff" stroke-opacity="0.14"/>
  <rect x="72" y="82" width="244" height="34" rx="17" fill="{c['accent']}" opacity="0.20"/>
  <text x="94" y="105" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="10" font-weight="900" fill="{c['accent']}" letter-spacing="2.4">PREMIUM BUSINESS TOOLKIT</text>
  <text x="{width-72}" y="104" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="10" font-weight="700" fill="{c['text_light']}" opacity="0.58" text-anchor="end">{_esc(kit_edition.upper())}</text>
  <g transform="translate(476 176) rotate(-10)">{_mini_stack(0, 0, c, 1.18)}</g>
  <rect x="72" y="164" width="104" height="104" rx="24" fill="url(#accentGrad)" filter="url(#shadow)"/>
  <text x="124" y="226" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="26" font-weight="900" fill="{c['primary']}" text-anchor="middle">KIT</text>
  <text x="72" y="292" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="12" font-weight="800" fill="{c['accent']}" letter-spacing="2.2">{doc_count} DOCUMENTS · PROMPTS · SYSTEMS · CHECKLISTS</text>
  {_text_lines(name_lines, 72, name_y, 54, 900, c["text_light"], 62)}
  <rect x="72" y="{tag_y - 20}" width="112" height="6" rx="3" fill="url(#accentGrad)"/>
  {_text_lines(tag_lines, 72, tag_y, 21, 500, c["text_light"], 32)}
  <g transform="translate(72 {height-402})">
    <rect width="{width-144}" height="86" rx="18" fill="{c['cream']}" opacity="0.97"/>
    <text x="26" y="33" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="11" font-weight="900" fill="{c['primary_2']}" letter-spacing="1.5">POSITIONING</text>
    <text x="26" y="62" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="17" font-weight="750" fill="{c['ink']}">A practical AI operating system for real estate agents.</text>
  </g>
  {doc_badges}
  <rect x="0" y="{height-70}" width="{width}" height="70" fill="#050b14" opacity="0.72"/>
  <text x="72" y="{height-31}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="11" font-weight="900" fill="{c['accent']}" letter-spacing="3">HYDRA</text>
  <text x="{width-72}" y="{height-31}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="10" font-weight="700" fill="rgba(255,255,255,0.48)" text-anchor="end">READY FOR GUMROAD · FIVERR · PAYHIP</text>
</svg>"""


def _marketplace_layout(width: int, height: int) -> dict[str, int]:
    scale = width / 1280
    safe_margin = int(76 * scale)
    left_column_width = int(560 * scale)
    right_visual_x = int(720 * scale)
    card_width = int(220 * scale)
    card_height = int(82 * scale)
    gutter_x = int(30 * scale)
    gutter_y = int(16 * scale)
    return {
        "canvas_width": width,
        "canvas_height": height,
        "safe_margin": safe_margin,
        "margin": safe_margin,
        "left_column_width": left_column_width,
        "title_box_width": left_column_width,
        "right_visual_x": right_visual_x,
        "module_grid_x": right_visual_x,
        "card_grid_x": right_visual_x,
        "card_grid_y": int(126 * scale),
        "module_grid_y": int(126 * scale),
        "card_width": card_width,
        "card_height": card_height,
        "gutter_x": gutter_x,
        "gutter_y": gutter_y,
        "title_y": int(214 * scale) if width == 1280 else int(242 * scale),
        "subtitle_y": 0,
        "bottom_panel_y": height - safe_margin - int(112 * scale),
        "safe_bottom_y": height - safe_margin - int(112 * scale),
        "bottom_chip_y": height - safe_margin - int(44 * scale),
        "major_zone_gap": int(40 * scale),
        "text_block_gap": int(32 * scale),
        "scale": scale,
    }


def _cards_grid(layout: dict[str, int], c: dict) -> str:
    cards = []
    for i, (num, _title, _subtitle, short) in enumerate(DOCUMENTS):
        col = i % 2
        row = i // 2
        x = layout["module_grid_x"] + col * (layout["card_width"] + layout["gutter_x"])
        y = layout["card_grid_y"] + row * (layout["card_height"] + layout["gutter_y"])
        cards.append(
            f'<rect x="{x}" y="{y}" width="{layout["card_width"]}" height="{layout["card_height"]}" rx="18" fill="{c["paper"]}" opacity="0.96" filter="url(#shadow)"/>'
            f'<rect x="{x}" y="{y}" width="{layout["card_width"]}" height="12" rx="6" fill="{c["accent"]}"/>'
            f'<text x="{x+20}" y="{y+36}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" font-weight="950" fill="{c["primary_2"]}">{num}</text>'
            f'<text x="{x+20}" y="{y+58}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="12" font-weight="800" fill="{c["ink"]}">{_esc(short)}</text>'
            f'<text x="{x+20}" y="{y+75}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="9" font-weight="650" fill="#64748b">ready-to-use module</text>'
        )
    return "\n".join(cards)


def _marketplace_layout_zones(kind: str, width: int, height: int, title_lines: list[str], sub_lines: list[str]) -> tuple[dict[str, int], dict[str, Rect], list[Rect]]:
    layout = _marketplace_layout(width, height)
    scale = layout["scale"]
    title_size = 54 if width == 1280 else 64
    title_gap = 60 if width == 1280 else 72
    sub_size = 21 if width == 1280 else 26
    sub_gap = 29 if width == 1280 else 34
    title_y = layout["title_y"]
    title_height = max(title_size, len(title_lines) * title_gap)
    subtitle_y = title_y + title_height + layout["text_block_gap"] + int(12 * scale)
    subtitle_height = max(sub_size, len(sub_lines) * sub_gap)
    accent_y = subtitle_y - int(38 * scale)

    title = Rect("title_safe_zone", layout["margin"] + int(20 * scale), title_y - title_size, layout["left_column_width"], title_height + int(18 * scale), "text_zone")
    accent = Rect("accent_line", title.x, accent_y, int(116 * scale), int(7 * scale), "accent")
    subtitle = Rect("subtitle_safe_zone", title.x, subtitle_y - sub_size, layout["left_column_width"], subtitle_height + int(14 * scale), "text_zone")

    cards = []
    for i in range(len(DOCUMENTS)):
        col = i % 2
        row = i // 2
        cards.append(
            Rect(
                f"module_card_{i+1}",
                layout["card_grid_x"] + col * (layout["card_width"] + layout["gutter_x"]),
                layout["card_grid_y"] + row * (layout["card_height"] + layout["gutter_y"]),
                layout["card_width"],
                layout["card_height"],
                "module_card",
            )
        )

    card_cluster = Rect(
        "module_card_cluster",
        layout["card_grid_x"],
        layout["card_grid_y"],
        layout["card_width"] * 2 + layout["gutter_x"],
        layout["card_height"] * 4 + layout["gutter_y"] * 3,
        "visual_zone",
    )

    bottom_panel = Rect("buyer_outcome_panel", title.x, layout["bottom_panel_y"], layout["left_column_width"], int(86 * scale), "bottom_panel")
    bottom_chip = Rect("hydra_footer_chip", width - layout["margin"] - int(224 * scale), layout["bottom_chip_y"], int(224 * scale), int(36 * scale), "footer_chip")

    zones = {
        "title": title,
        "accent": accent,
        "subtitle": subtitle,
        "card_cluster": card_cluster,
        "bottom_panel": bottom_panel,
        "bottom_chip": bottom_chip,
    }
    elements = [title, accent, subtitle, card_cluster, bottom_panel, bottom_chip, *cards]
    layout.update(
        {
            "title_size": title_size,
            "title_line_gap": title_gap,
            "subtitle_size": sub_size,
            "subtitle_line_gap": sub_gap,
            "subtitle_y": subtitle_y,
            "accent_y": accent_y,
            "bottom_panel_y": bottom_panel.y,
            "bottom_chip_y": bottom_chip.y,
        }
    )
    return layout, zones, elements


def validate_marketplace_layout(kind: str, width: int, height: int, elements: list[Rect]) -> dict:
    issues = {
        "collisions": [],
        "bounds_issues": [],
        "safe_zone_issues": [],
        "spacing_issues": [],
    }
    by_name = {item.name: item for item in elements}
    major_zone_gap = 40
    text_block_gap = 32

    for item in elements:
        if not item.inside(width, height):
            issues["bounds_issues"].append(f"{item.name} exceeds {width}x{height} viewBox")

    collision_pairs = [
        ("title_safe_zone", "subtitle_safe_zone", text_block_gap),
        ("accent_line", "title_safe_zone", 0),
        ("accent_line", "subtitle_safe_zone", 0),
        ("module_card_cluster", "title_safe_zone", major_zone_gap),
        ("module_card_cluster", "subtitle_safe_zone", major_zone_gap),
        ("buyer_outcome_panel", "subtitle_safe_zone", text_block_gap),
        ("buyer_outcome_panel", "module_card_cluster", major_zone_gap),
        ("hydra_footer_chip", "buyer_outcome_panel", major_zone_gap),
        ("hydra_footer_chip", "module_card_cluster", major_zone_gap),
    ]
    for left, right, gap in collision_pairs:
        a = by_name[left]
        b = by_name[right]
        if a.intersects(b, gap):
            issues["collisions"].append(f"{a.name} is too close to {b.name}; required gap {gap}px")

    cards = [item for item in elements if item.kind == "module_card"]
    for i, a in enumerate(cards):
        for b in cards[i + 1 :]:
            if a.intersects(b, 16):
                issues["spacing_issues"].append(f"{a.name} is too close to {b.name}")

    title = by_name["title_safe_zone"]
    card_cluster = by_name["module_card_cluster"]
    if card_cluster.x < title.right + major_zone_gap:
        issues["safe_zone_issues"].append("module cards enter title safe zone")
    if kind == "fiverr_gig_image" and (width, height) != (1280, 769):
        issues["safe_zone_issues"].append("Fiverr image must be 1280x769")
    if kind in ("gumroad_cover", "payhip_sellfy") and (width, height) != (1600, 900):
        issues["safe_zone_issues"].append("Gumroad/Payhip cover must be 1600x900")

    fail_count = sum(len(value) for value in issues.values())
    return {
        "asset_type": kind,
        "canvas": {"width": width, "height": height},
        "status": "PASS" if fail_count == 0 else "FAIL",
        "collisions_found": issues["collisions"],
        "bounds_issues": issues["bounds_issues"],
        "safe_zone_issues": issues["safe_zone_issues"],
        "spacing_issues": issues["spacing_issues"],
        "elements": [item.as_dict() for item in elements],
    }


def layout_safety_for_asset(kind: str, theme: str = "navy_gold") -> dict:
    width, height = (1600, 900) if kind in ("gumroad_cover", "payhip_sellfy") else (1280, 769)
    headline, subheadline = HEADLINE_VARIANTS.get(kind, HEADLINE_VARIANTS["gumroad_cover"])
    title_lines = _wrap_text_svg(headline, 25)
    sub_lines = _wrap_text_svg(subheadline, 38 if width == 1280 else 44)
    _layout, _zones, elements = _marketplace_layout_zones(kind, width, height, title_lines, sub_lines)
    result = validate_marketplace_layout(kind, width, height, elements)
    result["theme"] = theme
    result["recommended_fixes"] = _layout_fix_recommendations(result)
    return result


def _layout_fix_recommendations(result: dict) -> list[str]:
    fixes: list[str] = []
    if result["collisions_found"]:
        fixes.append("Increase safe-zone gaps or move the conflicting zone before export.")
    if result["bounds_issues"]:
        fixes.append("Move overflowing elements inside the SVG viewBox.")
    if result["safe_zone_issues"]:
        fixes.append("Separate text zones from visual modules and enforce platform dimensions.")
    if result["spacing_issues"]:
        fixes.append("Increase card gutters and reduce card density.")
    if not fixes:
        fixes.append("No deterministic layout fixes required.")
    return fixes


def build_layout_safety_report(product_dir: str | Path) -> dict:
    product_path = Path(product_dir)
    visuals_dir = product_path / "marketplace_visuals"
    quality_dir = product_path / "quality"
    quality_dir.mkdir(parents=True, exist_ok=True)

    assets: list[dict] = []
    for kind, filename in MARKETPLACE_FILES.items():
        path = visuals_dir / filename
        if path.exists():
            result = layout_safety_for_asset(kind, "main")
            result["filename"] = str(path)
            result["scope"] = "main"
            assets.append(result)

    variants_dir = visuals_dir / "variants"
    if variants_dir.exists():
        for theme_dir in sorted(p for p in variants_dir.iterdir() if p.is_dir()):
            for kind in ("gumroad_cover", "fiverr_gig_image", "value_stack", "included", "mockup"):
                filename = MARKETPLACE_FILES[kind]
                path = theme_dir / filename
                if path.exists():
                    result = layout_safety_for_asset(kind, theme_dir.name)
                    result["filename"] = str(path)
                    result["scope"] = f"variant:{theme_dir.name}"
                    assets.append(result)

    fail_count = sum(1 for asset in assets if asset["status"] == "FAIL")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "product_dir": str(product_path),
        "status": "PASS" if fail_count == 0 else "FAIL",
        "fail_count": fail_count,
        "asset_count": len(assets),
        "requirements": {
            "minimum_primary_text_gap_px": 32,
            "minimum_major_zone_gap_px": 40,
            "fiverr_dimensions": "1280x769",
            "gumroad_dimensions": "1600x900",
        },
        "assets": assets,
    }
    json_path = quality_dir / "layout_safety_report.json"
    md_path = quality_dir / "layout_safety_report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_layout_safety_markdown(report), encoding="utf-8")
    return report


def _layout_safety_markdown(report: dict) -> str:
    lines = [
        "# Layout Safety Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: {report['status']}",
        f"Assets checked: {report['asset_count']}",
        f"Failures: {report['fail_count']}",
        "",
        "## Requirements",
        "",
        "- No title/subtitle overlap.",
        "- No accent line through text.",
        "- No module cards inside title safe zone.",
        "- No bottom chip overlap.",
        "- All elements inside viewBox.",
        "- Minimum 32px between primary text blocks.",
        "- Minimum 40px between major composition zones.",
        "",
        "## Assets",
        "",
    ]
    for asset in report["assets"]:
        lines.append(f"### {asset['scope']} — {Path(asset['filename']).name}")
        lines.append("")
        lines.append(f"- Status: {asset['status']}")
        if asset["collisions_found"]:
            lines.append(f"- Collisions: {'; '.join(asset['collisions_found'])}")
        if asset["bounds_issues"]:
            lines.append(f"- Bounds: {'; '.join(asset['bounds_issues'])}")
        if asset["safe_zone_issues"]:
            lines.append(f"- Safe zones: {'; '.join(asset['safe_zone_issues'])}")
        if asset["spacing_issues"]:
            lines.append(f"- Spacing: {'; '.join(asset['spacing_issues'])}")
        lines.append(f"- Recommended fixes: {'; '.join(asset['recommended_fixes'])}")
        lines.append("")
    return "\n".join(lines)


def generate_marketplace_cover_svg(kind: str, kit_name: str, kit_tagline: str, theme: str = "navy_gold") -> str:
    c = KIT_COLORS.get(theme, KIT_COLORS["navy_gold"])
    width, height = (1600, 900) if kind in ("gumroad_cover", "payhip_sellfy") else (1280, 769)
    headline, subheadline = HEADLINE_VARIANTS.get(kind, HEADLINE_VARIANTS["gumroad_cover"])
    eyebrow = {
        "gumroad_cover": "GUMROAD-READY DIGITAL BUSINESS KIT",
        "fiverr_gig_image": "FIVERR-READY BUSINESS KIT",
        "value_stack": "$97 VALUE STACK",
        "included": "WHAT'S INCLUDED",
        "mockup": "PRODUCT MOCKUP",
        "payhip_sellfy": "PAYHIP / SELLFY COVER",
    }.get(kind, "MARKETPLACE COVER")
    title_lines = _wrap_text_svg(headline, 25)
    sub_lines = _wrap_text_svg(subheadline, 38 if width == 1280 else 44)
    layout, zones, elements = _marketplace_layout_zones(kind, width, height, title_lines, sub_lines)
    validation = validate_marketplace_layout(kind, width, height, elements)
    status = validation["status"]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<!-- HYDRA_LAYOUT_SAFETY: {status}; kind={kind}; theme={theme} -->
{_premium_background(width, height, c)}
  <rect x="{layout['margin']}" y="{layout['margin']}" width="{width - 2*layout['margin']}" height="{height - 2*layout['margin']}" rx="30" fill="#ffffff" opacity="0.070" stroke="#ffffff" stroke-opacity="0.15"/>
  <rect x="{layout['margin'] + 20}" y="{layout['margin'] + 22}" width="360" height="38" rx="19" fill="{c['accent']}" opacity="0.20"/>
  <text x="{layout['margin'] + 44}" y="{layout['margin'] + 47}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="12" font-weight="900" fill="{c['accent']}" letter-spacing="2.1">{_esc(eyebrow)}</text>

  <g>
    {_text_lines(title_lines, zones["title"].x, layout["title_y"], layout["title_size"], 920, c["text_light"], layout["title_line_gap"])}
    <rect x="{zones['accent'].x}" y="{zones['accent'].y}" width="{zones['accent'].width}" height="{zones['accent'].height}" rx="4" fill="url(#accentGrad)"/>
    {_text_lines(sub_lines, zones["subtitle"].x, layout["subtitle_y"], layout["subtitle_size"], 600, c["text_light"], layout["subtitle_line_gap"])}
  </g>

  <g>{_cards_grid(layout, c)}</g>

  <g transform="translate({zones['bottom_panel'].x} {zones['bottom_panel'].y})">
    <rect width="{layout['title_box_width']}" height="84" rx="18" fill="{c['cream']}" opacity="0.98" filter="url(#shadow)"/>
    <text x="28" y="31" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="12" font-weight="900" fill="{c['primary_2']}" letter-spacing="1.4">BUYER OUTCOME</text>
    <text x="28" y="59" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="17" font-weight="800" fill="{c['ink']}">Save time on listings, follow-up, client communication, content, and reviews.</text>
  </g>

  <rect x="{zones['bottom_chip'].x}" y="{zones['bottom_chip'].y}" width="{zones['bottom_chip'].width}" height="{zones['bottom_chip'].height}" rx="18" fill="{c['panel']}" opacity="0.72"/>
  <text x="{zones['bottom_chip'].x + zones['bottom_chip'].width // 2}" y="{zones['bottom_chip'].y + 23}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="11" font-weight="900" fill="{c['accent']}" text-anchor="middle" letter-spacing="2.4">HYDRA</text>
</svg>"""


def build_marketplace_visuals(product_dir: str | Path, kit_name: str, kit_tagline: str, theme: str = "navy_gold") -> dict[str, str]:
    visuals_dir = Path(product_dir) / "marketplace_visuals"
    visuals_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for kind, filename in MARKETPLACE_FILES.items():
        path = visuals_dir / filename
        path.write_text(generate_marketplace_cover_svg(kind, kit_name, kit_tagline, theme), encoding="utf-8")
        paths[filename] = str(path)
    paths.update(build_palette_variants(visuals_dir, kit_name, kit_tagline))
    report = build_layout_safety_report(Path(product_dir))
    paths["quality/layout_safety_report.json"] = str(Path(product_dir) / "quality" / "layout_safety_report.json")
    paths["quality/layout_safety_report.md"] = str(Path(product_dir) / "quality" / "layout_safety_report.md")
    return paths


def build_palette_variants(visuals_dir: str | Path, kit_name: str, kit_tagline: str) -> dict[str, str]:
    variants_dir = Path(visuals_dir) / "variants"
    variants_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for theme_key in PALETTES:
        theme_dir = variants_dir / theme_key
        theme_dir.mkdir(parents=True, exist_ok=True)
        for kind in ("gumroad_cover", "fiverr_gig_image", "value_stack", "included", "mockup"):
            filename = MARKETPLACE_FILES[kind]
            path = theme_dir / filename
            path.write_text(generate_marketplace_cover_svg(kind, kit_name, kit_tagline, theme_key), encoding="utf-8")
            paths[f"variants/{theme_key}/{filename}"] = str(path)
    index_path = variants_dir / "index.html"
    index_path.write_text(_variant_index_html(_variant_layout_statuses()), encoding="utf-8")
    paths["variants/index.html"] = str(index_path)
    notes_path = variants_dir / "export_notes.md"
    notes_path.write_text(_export_notes_markdown(), encoding="utf-8")
    paths["variants/export_notes.md"] = str(notes_path)
    return paths


def _variant_layout_statuses() -> dict[str, str]:
    statuses: dict[str, str] = {}
    for theme_key in PALETTES:
        checks = [
            layout_safety_for_asset(kind, theme_key)["status"]
            for kind in ("gumroad_cover", "fiverr_gig_image", "value_stack", "included", "mockup")
        ]
        statuses[theme_key] = "PASS" if all(status == "PASS" for status in checks) else "FAIL"
    return statuses


def _variant_index_html(layout_statuses: dict[str, str] | None = None) -> str:
    layout_statuses = layout_statuses or _variant_layout_statuses()
    swatches = {
        key: "".join(f'<span class="swatch" style="background:{palette[name]}"></span>' for name in ("primary", "accent", "cream"))
        for key, palette in PALETTES.items()
    }
    cards = "\n".join(
        f"""
        <section class="theme-card">
          <div class="theme-head">
            <div>
              <h2>{_esc(palette['name'])}</h2>
              <p>{_esc(palette['use_case'])}</p>
            </div>
            <div class="meta">
              <span class="status {layout_statuses.get(key, 'WARNING').lower()}">Layout {layout_statuses.get(key, 'WARNING')}</span>
              <div class="swatches">{swatches[key]}</div>
            </div>
          </div>
          <div class="preview-grid">
            <div><h3>Gumroad</h3><img src="{key}/gumroad_cover.svg" alt="{_esc(palette['name'])} Gumroad cover"></div>
            <div><h3>Fiverr 1280x769</h3><img src="{key}/fiverr_gig_image_1280x769.svg" alt="{_esc(palette['name'])} Fiverr image"></div>
          </div>
        </section>
        """
        for key, palette in PALETTES.items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Product 43 Visual Variants</title>
<style>
body {{ margin:0; font-family: Inter, Segoe UI, Arial, sans-serif; background:#f5f7fb; color:#111827; }}
main {{ width:min(1180px, calc(100% - 40px)); margin:34px auto 60px; }}
h1 {{ margin:0 0 8px; font-size:34px; }}
.intro {{ color:#526071; margin-bottom:26px; }}
.theme-card {{ background:#fff; border:1px solid #dfe5ef; border-radius:12px; padding:18px; margin-bottom:24px; box-shadow:0 10px 28px rgba(15,23,42,.06); }}
.theme-head {{ display:flex; justify-content:space-between; gap:20px; align-items:flex-start; margin-bottom:16px; }}
.meta {{ display:flex; align-items:center; gap:14px; }}
.status {{ display:inline-flex; align-items:center; height:28px; padding:0 11px; border-radius:999px; font-size:11px; font-weight:900; letter-spacing:.08em; }}
.status.pass {{ color:#065f46; background:#d1fae5; }}
.status.warning {{ color:#92400e; background:#fef3c7; }}
.status.fail {{ color:#991b1b; background:#fee2e2; }}
h2 {{ margin:0 0 4px; font-size:22px; }}
h3 {{ margin:0 0 8px; font-size:12px; text-transform:uppercase; letter-spacing:.12em; color:#64748b; }}
p {{ margin:0; color:#526071; }}
.swatches {{ display:flex; gap:8px; }}
.swatch {{ width:30px; height:30px; border-radius:50%; border:1px solid rgba(0,0,0,.12); }}
.preview-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
img {{ width:100%; display:block; border-radius:10px; border:1px solid #e5e7eb; background:#fff; }}
@media (max-width: 800px) {{ .preview-grid {{ grid-template-columns:1fr; }} .theme-head {{ flex-direction:column; }} }}
</style>
</head>
<body>
<main>
  <h1>Product 43 Marketplace Visual Variants</h1>
  <p class="intro">Compare deterministic palette directions for the Real Estate AI Mastery Kit. Recommended first test: Navy Gold.</p>
  {cards}
</main>
</body>
</html>"""


def _export_notes_markdown() -> str:
    return """# Product 43 Marketplace Visual Export Notes

Recommended theme: **Navy Gold**.

## Gumroad

Export:

- `variants/navy_gold/gumroad_cover.svg`
- Optional gallery: `variants/navy_gold/value_stack.svg`
- Optional gallery: `variants/navy_gold/eight_documents_included.svg`
- Optional gallery: `variants/navy_gold/product_mockup.svg`

## Fiverr

Export:

- `variants/navy_gold/fiverr_gig_image_1280x769.svg`

Fiverr expects raster uploads in practice, so export this SVG to PNG/JPG before upload.

## Manual Export Suggestions

If available locally:

```bash
rsvg-convert -w 1600 -h 900 variants/navy_gold/gumroad_cover.svg -o gumroad_cover.png
rsvg-convert -w 1280 -h 769 variants/navy_gold/fiverr_gig_image_1280x769.svg -o fiverr_gig_image.png
```

Alternative: open the SVG in a browser or design tool and export PNG manually.

## Notes

This sprint intentionally does not require PNG export. The folder structure is ready for a future export step.
"""


def build_kit_covers(
    product_dir: str | Path,
    kit_name: str,
    kit_tagline: str,
    kit_edition: str = "2026 Edition",
    theme: str = "navy_gold",
) -> dict[str, str]:
    covers_dir = Path(product_dir) / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for num, title, subtitle, _short in DOCUMENTS:
        path = covers_dir / f"cover_{num}.svg"
        path.write_text(generate_document_cover_svg(num, title, subtitle, kit_name, kit_edition, theme), encoding="utf-8")
        paths[path.name] = str(path)
    master_path = covers_dir / "cover_MASTER.svg"
    master_path.write_text(generate_master_cover_svg(kit_name, kit_tagline, kit_edition, len(DOCUMENTS), theme), encoding="utf-8")
    paths[master_path.name] = str(master_path)
    paths.update(build_marketplace_visuals(product_dir, kit_name, kit_tagline, theme))
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
        print(f"  OK {fname} -> {path}")
    print(f"\n{len(result)} visual assets written under {out}")
