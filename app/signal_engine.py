from __future__ import annotations


def _value(candidate: dict, key: str) -> float:
    try:
        return float(candidate.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def calculate_score(candidate: dict) -> float:
    """Return a deterministic SIGNAL score normalized to 0-100."""
    raw_score = (
        0.30 * _value(candidate, "demand_velocity")
        + 0.20 * _value(candidate, "monetization_fit")
        + 0.20 * _value(candidate, "ai_exploitability")
        + 0.15 * _value(candidate, "cross_source_confirmation")
        + 0.15 * _value(candidate, "time_to_revenue")
        - 0.20 * _value(candidate, "saturation_penalty")
        - 0.10 * _value(candidate, "platform_risk_penalty")
    )
    return round(max(0.0, min(100.0, raw_score)), 2)


MOCK_CANDIDATES = [
    {
        "source": "Google Trends + Product Hunt",
        "topic": "AI meeting note cleanup kit for solo consultants",
        "vertical": "creator economy tools",
        "production_format": "prompt pack + workflow PDF",
        "demand_velocity": 92,
        "monetization_fit": 86,
        "ai_exploitability": 94,
        "cross_source_confirmation": 82,
        "time_to_revenue": 88,
        "saturation_penalty": 28,
        "platform_risk_penalty": 18,
        "evidence": "Search interest rising for AI meeting notes; Product Hunt launches cluster around meeting summaries; consultants complain about cleanup time.",
    },
    {
        "source": "Reddit",
        "topic": "Landlord repair request letter templates",
        "vertical": "local life admin",
        "production_format": "editable template bundle",
        "demand_velocity": 78,
        "monetization_fit": 80,
        "ai_exploitability": 74,
        "cross_source_confirmation": 61,
        "time_to_revenue": 84,
        "saturation_penalty": 22,
        "platform_risk_penalty": 12,
        "evidence": "Repeated tenant advice threads ask for written repair notices; simple PDF/doc templates can be produced quickly.",
    },
    {
        "source": "TikTok + Pinterest seasonal search",
        "topic": "Summer camp packing checklist printables",
        "vertical": "seasonal printables",
        "production_format": "printable PDF pack",
        "demand_velocity": 86,
        "monetization_fit": 72,
        "ai_exploitability": 68,
        "cross_source_confirmation": 74,
        "time_to_revenue": 91,
        "saturation_penalty": 34,
        "platform_risk_penalty": 10,
        "evidence": "Seasonal planning searches are climbing; parents ask for age-specific camp packing lists and label checklists.",
    },
    {
        "source": "Product Hunt",
        "topic": "AI browser extension comparison cheat sheet",
        "vertical": "AI tools",
        "production_format": "cheat sheet PDF",
        "demand_velocity": 89,
        "monetization_fit": 76,
        "ai_exploitability": 81,
        "cross_source_confirmation": 79,
        "time_to_revenue": 86,
        "saturation_penalty": 36,
        "platform_risk_penalty": 20,
        "evidence": "New AI browser assistants launch weekly; buyers need concise feature/pricing comparisons before trying tools.",
    },
    {
        "source": "Reddit + Google Trends",
        "topic": "Notion ADHD student semester command center",
        "vertical": "study planners",
        "production_format": "Notion template",
        "demand_velocity": 84,
        "monetization_fit": 88,
        "ai_exploitability": 72,
        "cross_source_confirmation": 77,
        "time_to_revenue": 76,
        "saturation_penalty": 42,
        "platform_risk_penalty": 16,
        "evidence": "Students ask for low-friction semester systems; Notion template marketplace has buyer familiarity but crowded supply.",
    },
    {
        "source": "Local business forums",
        "topic": "Missed-call SMS follow-up scripts for home services",
        "vertical": "local business automation",
        "production_format": "script pack + setup guide",
        "demand_velocity": 81,
        "monetization_fit": 91,
        "ai_exploitability": 79,
        "cross_source_confirmation": 68,
        "time_to_revenue": 79,
        "saturation_penalty": 25,
        "platform_risk_penalty": 22,
        "evidence": "Plumbers and cleaners report missed leads; automation advice threads ask for copy-and-paste SMS follow-ups.",
    },
    {
        "source": "Reddit pain points",
        "topic": "First-time manager one-on-one question bank",
        "vertical": "career templates",
        "production_format": "template PDF + docs",
        "demand_velocity": 70,
        "monetization_fit": 77,
        "ai_exploitability": 75,
        "cross_source_confirmation": 58,
        "time_to_revenue": 82,
        "saturation_penalty": 29,
        "platform_risk_penalty": 8,
        "evidence": "New managers ask how to run useful one-on-ones; lightweight templates fit impulse digital-product purchase.",
    },
    {
        "source": "Google Trends",
        "topic": "Wedding vendor email scripts",
        "vertical": "seasonal printables",
        "production_format": "editable email template bundle",
        "demand_velocity": 75,
        "monetization_fit": 83,
        "ai_exploitability": 70,
        "cross_source_confirmation": 64,
        "time_to_revenue": 78,
        "saturation_penalty": 31,
        "platform_risk_penalty": 11,
        "evidence": "Wedding planning searches rise seasonally; couples look for negotiation, follow-up, and cancellation wording.",
    },
    {
        "source": "Creator newsletters",
        "topic": "Short-form content repurposing prompt pack",
        "vertical": "creator economy tools",
        "production_format": "prompt pack",
        "demand_velocity": 79,
        "monetization_fit": 85,
        "ai_exploitability": 93,
        "cross_source_confirmation": 72,
        "time_to_revenue": 89,
        "saturation_penalty": 55,
        "platform_risk_penalty": 24,
        "evidence": "Creators ask how to turn long videos into posts; demand is strong, but prompt-pack saturation is high.",
    },
    {
        "source": "Product Hunt + X",
        "topic": "AI image model style reference organizer",
        "vertical": "AI tools",
        "production_format": "Airtable/Notion template",
        "demand_velocity": 73,
        "monetization_fit": 71,
        "ai_exploitability": 77,
        "cross_source_confirmation": 67,
        "time_to_revenue": 74,
        "saturation_penalty": 38,
        "platform_risk_penalty": 19,
        "evidence": "Designers compare image models and lose track of style references; template can organize prompts, outputs, and licenses.",
    },
    {
        "source": "Reddit + forums",
        "topic": "Small claims court preparation checklist",
        "vertical": "life admin",
        "production_format": "checklist PDF",
        "demand_velocity": 69,
        "monetization_fit": 79,
        "ai_exploitability": 62,
        "cross_source_confirmation": 66,
        "time_to_revenue": 73,
        "saturation_penalty": 24,
        "platform_risk_penalty": 36,
        "evidence": "People ask what documents to bring to small claims court; legal-adjacent wording requires careful disclaimers.",
    },
    {
        "source": "Back-to-school search",
        "topic": "SAT study sprint planner",
        "vertical": "study planners",
        "production_format": "printable planner PDF",
        "demand_velocity": 77,
        "monetization_fit": 74,
        "ai_exploitability": 66,
        "cross_source_confirmation": 70,
        "time_to_revenue": 81,
        "saturation_penalty": 33,
        "platform_risk_penalty": 9,
        "evidence": "Study schedule searches rise before test windows; parents and students buy printable planners and trackers.",
    },
]


def mock_candidates() -> list[dict]:
    candidates = []
    for candidate in MOCK_CANDIDATES:
        scored = dict(candidate)
        scored["score"] = calculate_score(scored)
        candidates.append(scored)
    return candidates
