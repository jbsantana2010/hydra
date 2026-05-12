from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


REQUIRED_VISUALS = [
    "gumroad_cover.svg",
    "fiverr_gig_image_1280x769.svg",
    "value_stack.svg",
    "eight_documents_included.svg",
    "product_mockup.svg",
]

DIMENSIONS = {
    "gumroad_cover.svg": (1600, 900),
    "fiverr_gig_image_1280x769.svg": (1280, 769),
}

THEME_GUIDANCE = {
    "navy_gold": {
        "name": "Navy Gold",
        "use_case": "best all-around premium consulting positioning",
        "contrast": 91,
        "premium": 94,
        "marketplace": 92,
    },
    "charcoal_emerald": {
        "name": "Charcoal Emerald",
        "use_case": "high-trust business operations positioning",
        "contrast": 88,
        "premium": 89,
        "marketplace": 88,
    },
    "white_navy_gold": {
        "name": "White Navy Gold",
        "use_case": "bright marketplace thumbnails and Pinterest-friendly previews",
        "contrast": 84,
        "premium": 86,
        "marketplace": 90,
    },
    "deep_teal_copper": {
        "name": "Deep Teal Copper",
        "use_case": "luxury real estate and boutique consulting positioning",
        "contrast": 86,
        "premium": 91,
        "marketplace": 86,
    },
    "black_platinum_blue": {
        "name": "Black Platinum Blue",
        "use_case": "AI-forward, technical premium positioning",
        "contrast": 90,
        "premium": 88,
        "marketplace": 87,
    },
}

OUTCOME_WORDS = (
    "close more deals",
    "less time",
    "follow-up",
    "listings",
    "client",
    "workflow",
    "assistant",
    "prompts",
    "scripts",
    "modern agents",
)

HEADLINE_CANDIDATES = (
    "Real Estate AI Mastery Kit",
    "Close More Deals in Less Time With AI",
    "AI Systems for Real Estate Agents",
    "The Real Estate Agent AI Toolkit",
    "Turn AI Into Your Real Estate Assistant",
)


def run_aesthetica_review(product_id: int, product_root: str | Path = "products") -> dict[str, Any]:
    """Run deterministic marketplace-visual scoring for one product package."""
    product_dir = Path(product_root) / f"product_{product_id}"
    variants_dir = product_dir / "marketplace_visuals" / "variants"
    quality_dir = product_dir / "quality"
    agent_dir = product_dir / "agent_reviews" / "aesthetica"
    quality_dir.mkdir(parents=True, exist_ok=True)
    agent_dir.mkdir(parents=True, exist_ok=True)
    layout_report = _load_or_build_layout_report(product_dir)
    layout_by_theme = _layout_status_by_theme(layout_report)

    variant_reviews = []
    if variants_dir.exists():
        for theme_dir in sorted(p for p in variants_dir.iterdir() if p.is_dir()):
            variant_reviews.append(_review_variant(theme_dir, layout_by_theme.get(theme_dir.name, {})))

    if variant_reviews:
        best_gumroad = max(variant_reviews, key=lambda item: item["platform_scores"]["gumroad"])
        best_fiverr = max(variant_reviews, key=lambda item: item["platform_scores"]["fiverr"])
        best_overall = max(variant_reviews, key=lambda item: item["overall_score"])
        overall_score = round(mean(item["overall_score"] for item in variant_reviews), 1)
        required_fixes = _required_fixes(variant_reviews)
        weakest_layout_issue = _weakest_issue(variant_reviews)
        layout_safety_pass = layout_report.get("status") == "PASS"
        launch_ready = (
            best_overall["overall_score"] >= 80
            and not any(item["hard_blockers"] for item in variant_reviews)
            and layout_safety_pass
        )
    else:
        best_gumroad = best_fiverr = best_overall = None
        overall_score = 0.0
        required_fixes = ["Generate marketplace visual variants before launch."]
        weakest_layout_issue = "No marketplace visual variants were found."
        layout_safety_pass = False
        launch_ready = False

    strongest_headline = _strongest_headline(variant_reviews)
    generated_at = datetime.now(timezone.utc).isoformat()
    report = {
        "agent": "AESTHETICA",
        "agent_version": "0.1",
        "product_id": product_id,
        "generated_at": generated_at,
        "launch_ready": launch_ready,
        "overall_score": overall_score,
        "layout_safety": {
            "status": layout_report.get("status", "UNKNOWN"),
            "fail_count": layout_report.get("fail_count"),
            "asset_count": layout_report.get("asset_count"),
            "report_json": str(product_dir / "quality" / "layout_safety_report.json"),
            "launch_blocker": not layout_safety_pass,
        },
        "best_gumroad_theme": _theme_summary(best_gumroad, "gumroad"),
        "best_fiverr_theme": _theme_summary(best_fiverr, "fiverr"),
        "strongest_headline": strongest_headline,
        "weakest_layout_issue": weakest_layout_issue,
        "required_fixes_before_launch": required_fixes,
        "themes_reviewed": [item["theme"] for item in variant_reviews],
        "variant_reviews": variant_reviews,
        "output_paths": {
            "quality_json": str(quality_dir / "aesthetica_review.json"),
            "quality_markdown": str(quality_dir / "aesthetica_review.md"),
            "hermes_latest": str(agent_dir / "latest.json"),
        },
    }

    (quality_dir / "aesthetica_review.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (quality_dir / "aesthetica_review.md").write_text(
        _render_markdown(report), encoding="utf-8"
    )
    (agent_dir / "latest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _review_variant(theme_dir: Path, layout_status: dict[str, Any] | None = None) -> dict[str, Any]:
    theme_key = theme_dir.name
    guidance = THEME_GUIDANCE.get(theme_key, {})
    layout_status = layout_status or {}
    missing = [name for name in REQUIRED_VISUALS if not (theme_dir / name).exists()]
    hard_blockers = [f"Missing {name}" for name in missing]
    svg_infos = {name: _svg_info(theme_dir / name) for name in REQUIRED_VISUALS if (theme_dir / name).exists()}

    spacing = _score_spacing(svg_infos)
    headline = _score_headline(svg_infos)
    thumbnail = _score_thumbnail(svg_infos)
    hierarchy = _score_hierarchy(svg_infos)
    contrast = guidance.get("contrast", 78)
    buyer_outcome = _score_buyer_outcome(svg_infos)
    marketplace = min(guidance.get("marketplace", 78), 100) - len(missing) * 10
    premium = guidance.get("premium", 78)
    density = _score_density(svg_infos)
    safe_zone_score = _score_layout_safety(layout_status)
    spacing_discipline = min(spacing, safe_zone_score)

    dimensions_ok = _dimensions_ok(svg_infos)
    if not dimensions_ok:
        hard_blockers.append("One or more marketplace SVGs have incorrect dimensions.")
    if layout_status.get("status") == "FAIL":
        hard_blockers.append("Layout safety failed for this theme.")

    dimension_scores = {
        "spacing_collision_risk": spacing,
        "safe_zone_score": safe_zone_score,
        "spacing_discipline": spacing_discipline,
        "headline_clarity": headline,
        "thumbnail_readability": thumbnail,
        "hierarchy": hierarchy,
        "contrast": contrast,
        "buyer_outcome_clarity": buyer_outcome,
        "marketplace_fit": max(0, marketplace),
        "premium_feel": premium,
        "visual_density": density,
    }
    overall = round(mean(dimension_scores.values()), 1)
    notes = _variant_notes(theme_key, dimension_scores, hard_blockers)

    return {
        "theme": theme_key,
        "theme_name": guidance.get("name", theme_key.replace("_", " ").title()),
        "recommended_use_case": guidance.get("use_case", "general marketplace test"),
        "overall_score": overall,
        "dimension_scores": dimension_scores,
        "platform_scores": {
            "gumroad": round(mean([overall, premium, buyer_outcome, marketplace]), 1),
            "fiverr": round(mean([overall, thumbnail, headline, contrast]), 1),
            "pinterest": round(mean([thumbnail, contrast, buyer_outcome, density]), 1),
            "payhip_sellfy": round(mean([overall, marketplace, premium]), 1),
        },
        "layout_safety": {
            "status": layout_status.get("status", "UNKNOWN"),
            "fail_count": layout_status.get("fail_count", 0),
            "collision_risk": "low" if layout_status.get("status") == "PASS" else "high",
            "safe_zone_score": safe_zone_score,
            "spacing_discipline": spacing_discipline,
            "thumbnail_readability_impact": "none"
            if layout_status.get("status") == "PASS"
            else "layout failure may reduce thumbnail readability",
        },
        "files_present": sorted(svg_infos.keys()),
        "missing_files": missing,
        "hard_blockers": hard_blockers,
        "notes": notes,
    }


def _svg_info(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    width, height = _parse_dimensions(text)
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "width": width,
        "height": height,
        "text": text,
        "text_count": len(re.findall(r"<text\b", text)),
        "rect_count": len(re.findall(r"<rect\b", text)),
        "line_count": len(re.findall(r"<line\b", text)),
    }


def _parse_dimensions(svg: str) -> tuple[int | None, int | None]:
    width_match = re.search(r'\bwidth="([0-9]+)', svg)
    height_match = re.search(r'\bheight="([0-9]+)', svg)
    if width_match and height_match:
        return int(width_match.group(1)), int(height_match.group(1))
    viewbox_match = re.search(r'\bviewBox="[^"]*?\s([0-9]+)\s([0-9]+)"', svg)
    if viewbox_match:
        return int(viewbox_match.group(1)), int(viewbox_match.group(2))
    return None, None


def _all_text(svg_infos: dict[str, dict[str, Any]]) -> str:
    return "\n".join(info["text"] for info in svg_infos.values()).lower()


def _dimensions_ok(svg_infos: dict[str, dict[str, Any]]) -> bool:
    for name, expected in DIMENSIONS.items():
        info = svg_infos.get(name)
        if not info:
            return False
        if (info["width"], info["height"]) != expected:
            return False
    return True


def _load_or_build_layout_report(product_dir: Path) -> dict[str, Any]:
    path = product_dir / "quality" / "layout_safety_report.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    try:
        from kit_covers import build_layout_safety_report

        return build_layout_safety_report(product_dir)
    except Exception as exc:
        return {
            "status": "FAIL",
            "fail_count": 1,
            "asset_count": 0,
            "error": f"layout safety unavailable: {exc}",
            "assets": [],
        }


def _layout_status_by_theme(layout_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_theme: dict[str, dict[str, Any]] = {}
    for asset in layout_report.get("assets", []):
        theme = asset.get("theme")
        if not theme or theme == "main":
            continue
        bucket = by_theme.setdefault(theme, {"status": "PASS", "fail_count": 0, "assets": []})
        bucket["assets"].append(asset)
        if asset.get("status") == "FAIL":
            bucket["status"] = "FAIL"
            bucket["fail_count"] += 1
    return by_theme


def _score_layout_safety(layout_status: dict[str, Any]) -> int:
    if not layout_status:
        return 70
    if layout_status.get("status") == "PASS":
        return 96
    fail_count = int(layout_status.get("fail_count") or 1)
    return max(35, 82 - fail_count * 12)


def _score_spacing(svg_infos: dict[str, dict[str, Any]]) -> int:
    if not svg_infos:
        return 0
    score = 88
    for info in svg_infos.values():
        if info["bytes"] < 3500:
            score -= 8
        if info["text_count"] > 72:
            score -= 6
        if info["rect_count"] > 80:
            score -= 4
    return max(45, min(96, score))


def _score_headline(svg_infos: dict[str, dict[str, Any]]) -> int:
    text = _all_text(svg_infos)
    hits = sum(1 for phrase in HEADLINE_CANDIDATES if phrase.lower() in text)
    if hits >= 2:
        return 94
    if hits == 1:
        return 88
    if "real estate" in text and "ai" in text:
        return 82
    return 66


def _score_thumbnail(svg_infos: dict[str, dict[str, Any]]) -> int:
    fiverr = svg_infos.get("fiverr_gig_image_1280x769.svg")
    if not fiverr:
        return 0
    score = 88
    if (fiverr["width"], fiverr["height"]) == (1280, 769):
        score += 6
    if fiverr["text_count"] > 55:
        score -= 8
    if "buyer outcome" in fiverr["text"].lower():
        score += 3
    return max(50, min(97, score))


def _score_hierarchy(svg_infos: dict[str, dict[str, Any]]) -> int:
    text = _all_text(svg_infos)
    score = 82
    for token in ("buyer outcome", "included", "workflow", "documents", "hydra"):
        if token in text:
            score += 3
    return min(score, 95)


def _score_buyer_outcome(svg_infos: dict[str, dict[str, Any]]) -> int:
    text = _all_text(svg_infos)
    hits = sum(1 for word in OUTCOME_WORDS if word in text)
    return max(62, min(96, 68 + hits * 4))


def _score_density(svg_infos: dict[str, dict[str, Any]]) -> int:
    if not svg_infos:
        return 0
    avg_bytes = mean(info["bytes"] for info in svg_infos.values())
    avg_text = mean(info["text_count"] for info in svg_infos.values())
    score = 88
    if avg_bytes < 5000:
        score -= 12
    elif avg_bytes > 36000:
        score -= 8
    if avg_text < 10:
        score -= 10
    elif avg_text > 65:
        score -= 8
    return max(50, min(95, score))


def _variant_notes(theme_key: str, scores: dict[str, int], hard_blockers: list[str]) -> list[str]:
    notes = []
    if hard_blockers:
        notes.extend(hard_blockers)
    weakest = min(scores, key=scores.get)
    notes.append(f"Weakest dimension: {weakest.replace('_', ' ')} ({scores[weakest]}/100).")
    if theme_key == "navy_gold":
        notes.append("Strong premium consulting signal; best default for a $97 Gumroad test.")
    elif theme_key == "white_navy_gold":
        notes.append("Brightest marketplace option; useful when thumbnail clarity matters most.")
    elif theme_key == "deep_teal_copper":
        notes.append("Luxury real estate tone; good alternate for boutique-agent positioning.")
    return notes


def _required_fixes(variant_reviews: list[dict[str, Any]]) -> list[str]:
    fixes = []
    for review in variant_reviews:
        for blocker in review["hard_blockers"]:
            fixes.append(f"{review['theme_name']}: {blocker}")
    if not fixes:
        fixes.extend(
            [
                "Export the selected SVG cover assets to PNG/JPG before marketplace upload.",
                "Inspect the selected Fiverr image at search-thumbnail size before publishing.",
                "Keep Product 43 positioned around time savings, follow-up quality, and listing speed.",
            ]
        )
    return fixes


def _weakest_issue(variant_reviews: list[dict[str, Any]]) -> str:
    if not variant_reviews:
        return "No visual variants exist yet."
    weakest_review = min(
        variant_reviews,
        key=lambda item: min(item["dimension_scores"].values()),
    )
    weakest_dimension = min(
        weakest_review["dimension_scores"],
        key=weakest_review["dimension_scores"].get,
    )
    label = weakest_dimension.replace("_", " ")
    return f"{weakest_review['theme_name']} has the weakest {label} score."


def _strongest_headline(variant_reviews: list[dict[str, Any]]) -> str:
    text = "\n".join(
        info
        for review in variant_reviews
        for info in [json.dumps(review)]
    ).lower()
    for phrase in HEADLINE_CANDIDATES:
        if phrase.lower() in text:
            return phrase
    return "Real Estate AI Mastery Kit - Close More Deals in Less Time With AI"


def _theme_summary(review: dict[str, Any] | None, platform: str) -> dict[str, Any] | None:
    if not review:
        return None
    return {
        "theme": review["theme"],
        "theme_name": review["theme_name"],
        "score": review["platform_scores"][platform],
        "recommended_use_case": review["recommended_use_case"],
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AESTHETICA Visual Review",
        "",
        f"Product: {report['product_id']}",
        f"Generated: {report['generated_at']}",
        f"Overall score: {report['overall_score']}/100",
        f"Launch ready: {'yes' if report['launch_ready'] else 'no'}",
        f"Layout safety: {report['layout_safety']['status']}",
        "",
        "## Recommendation",
        "",
        f"- Best Gumroad theme: {_format_theme(report['best_gumroad_theme'])}",
        f"- Best Fiverr theme: {_format_theme(report['best_fiverr_theme'])}",
        f"- Strongest headline: {report['strongest_headline']}",
        f"- Weakest layout issue: {report['weakest_layout_issue']}",
        "",
        "## Required Fixes Before Launch",
        "",
    ]
    lines.extend(f"- {fix}" for fix in report["required_fixes_before_launch"])
    lines.extend(["", "## Theme Scores", ""])
    for review in report["variant_reviews"]:
        lines.append(f"### {review['theme_name']}")
        lines.append("")
        lines.append(f"- Overall: {review['overall_score']}/100")
        lines.append(f"- Gumroad: {review['platform_scores']['gumroad']}/100")
        lines.append(f"- Fiverr: {review['platform_scores']['fiverr']}/100")
        lines.append(f"- Pinterest: {review['platform_scores']['pinterest']}/100")
        lines.append(f"- Use case: {review['recommended_use_case']}")
        for note in review["notes"]:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)


def _format_theme(summary: dict[str, Any] | None) -> str:
    if not summary:
        return "none"
    return f"{summary['theme_name']} ({summary['score']}/100) - {summary['recommended_use_case']}"
