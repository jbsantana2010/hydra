"""
kit_llm_adapter.py — Bridges call_llm_json() to the kit_generator.py llm_call_fn interface.
Sprint 2.3.

Usage:
    from kit_llm_adapter import make_kit_llm_caller
    llm_call_fn = make_kit_llm_caller(db)
    results = generate_kit(..., llm_call_fn=llm_call_fn)

The returned callable accepts (system_prompt, user_prompt) and returns list[dict] of
section objects. Raises LlmBlocked or LlmFailed on policy/provider failure so the
caller (generate_kit) can apply deterministic fallback. All spend flows through
call_llm_json — no direct provider SDK usage.
"""
from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)

# Schema hint instructs the LLM to return {"sections": [...]} not a bare array.
# call_llm_json enforces JSON-object return at the parser level.
_SCHEMA_HINT: dict = {
    "sections": [
        {
            "type": "prose|workflow|prompt_block|callout|checklist|table|quick_win_box|roadmap|divider|page_break",
            "heading": "Section heading (string, omit for divider/page_break)",
            "level": 2,
            "paragraphs": ["paragraph text (for prose type)"],
            "intro": "intro text (for workflow/prompt_block/checklist/table)",
            "steps": [{"title": "...", "description": "...", "note": "(optional)"}],
            "prompts": [{"name": "...", "text": "...", "fill_in_fields": ["[FIELD]"], "example_output": "..."}],
            "items": [{"title": "...", "detail": "..."}],
            "columns": ["Col1", "Col2"],
            "rows": [["cell", "cell"]],
            "variant": "quick_win|pro_tip|time_saver|warning",
            "title": "callout/quick_win_box title",
            "content": "callout content",
            "description": "quick_win_box description",
            "time": "30 min",
            "phases": [{"title": "...", "time": "Week 1", "tasks": ["..."]}],
            "label": "divider label (for divider type)",
        }
    ]
}


def make_kit_llm_caller(db) -> Callable:
    """Return a kit-compatible LLM caller closure bound to the given DB session.

    The closure signature matches llm_call_fn in generate_kit():
        fn(system_prompt: str, user_prompt: str) -> list[dict]

    On LlmBlocked or LlmFailed, the exception propagates so generate_kit()
    can record the error and fall back to _fallback_sections() per document.
    """
    from llm import call_llm_json, LlmBlocked, LlmFailed  # noqa: F401 (re-exported for callers)

    def _call(system_prompt: str, user_prompt: str) -> list:
        data = call_llm_json(
            db=db,
            purpose="kit_doc_sections",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_hint=_SCHEMA_HINT,
            max_cost_usd=0.30,
            timeout_seconds=90,
        )
        sections = data.get("sections")
        if not isinstance(sections, list):
            raise ValueError(
                f"LLM returned 'sections' of type {type(sections).__name__}, expected list. "
                f"Keys present: {list(data.keys())}"
            )
        if not sections:
            raise ValueError("LLM returned empty sections list — prompt may be malformed")
        logger.info("kit_llm_adapter: received %d sections", len(sections))
        return sections

    return _call
