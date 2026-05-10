from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import func, select

from db import LlmCall, SystemActionBlocked, SystemFlag, assert_system_can_act

ANTHROPIC_MODEL = "claude-3-5-haiku-20241022"
OPENAI_MODEL = "gpt-4o-mini"
PER_CALL_CAP_USD = Decimal(os.getenv("HYDRA_LLM_PER_CALL_CAP_USD", "0.20"))

# Conservative public list prices. These are intentionally rounded up for safety.
PRICING = {
    "anthropic": {"input": Decimal("0.00000025"), "output": Decimal("0.00000125")},
    "openai": {"input": Decimal("0.00000020"), "output": Decimal("0.00000080")},
}


class LlmBlocked(Exception):
    """Raised when budget, kill-switch, or missing-key policy blocks a call."""


class LlmFailed(Exception):
    """Raised when providers fail or return invalid JSON."""


@dataclass
class Provider:
    name: str
    model: str
    api_key: str


def get_today_llm_spend(db) -> float:
    today = date.today()
    total = db.scalar(
        select(func.coalesce(func.sum(LlmCall.cost_usd), 0)).where(
            func.date(LlmCall.created_at) == today
        )
    )
    return float(total or 0)


def call_llm_json(
    db,
    purpose: str,
    system_prompt: str,
    user_prompt: str,
    schema_hint: dict,
    max_cost_usd: float = 0.20,
    timeout_seconds: int = 30,
    reverse_providers: bool = False,
) -> dict:
    """Call the configured LLM providers and return parsed JSON only.

    All LLM spend must pass through this function. Callers should catch
    LlmBlocked/LlmFailed and use deterministic fallbacks.
    """
    max_cost = min(Decimal(str(max_cost_usd)), PER_CALL_CAP_USD)
    started = time.monotonic()
    prompt_tokens = _estimate_tokens(system_prompt + "\n" + user_prompt + "\n" + json.dumps(schema_hint))
    completion_tokens = _completion_budget_for(purpose)
    estimated_cost = _estimate_cost("anthropic", prompt_tokens, completion_tokens)

    try:
        assert_system_can_act("llm_call")
        if Decimal(str(max_cost_usd)) > PER_CALL_CAP_USD:
            raise LlmBlocked(f"Per-call cap exceeded: requested ${max_cost_usd}, cap ${PER_CALL_CAP_USD}")
        if estimated_cost > max_cost:
            raise LlmBlocked(f"Estimated cost ${estimated_cost} exceeds call cap ${max_cost}")

        daily_budget = _get_daily_budget(db)
        today_spend = Decimal(str(get_today_llm_spend(db)))
        if today_spend + estimated_cost > daily_budget:
            raise LlmBlocked(
                f"Daily LLM budget exceeded: spend ${today_spend} + estimate ${estimated_cost} > cap ${daily_budget}"
            )

        providers = _providers(reverse=reverse_providers)
        if not providers:
            raise LlmBlocked("No LLM API key configured")

        errors: list[str] = []
        for provider in providers:
            content: str | None = None
            try:
                content, usage = _call_provider(
                    provider,
                    system_prompt,
                    user_prompt,
                    schema_hint,
                    completion_tokens,
                    timeout_seconds,
                )
                try:
                    data = _parse_json_object(content)
                except ValueError as exc:
                    raise ValueError(_format_json_parse_error(exc, content)) from exc
                actual_prompt = int(usage.get("prompt_tokens") or prompt_tokens)
                actual_completion = int(usage.get("completion_tokens") or _estimate_tokens(content))
                cost = _estimate_cost(provider.name, actual_prompt, actual_completion)
                duration = int((time.monotonic() - started) * 1000)
                _log_call(
                    db,
                    provider=provider.name,
                    model=provider.model,
                    purpose=purpose,
                    prompt_tokens=actual_prompt,
                    completion_tokens=actual_completion,
                    cost_usd=cost,
                    duration_ms=duration,
                    status="success",
                    error=None,
                )
                return data
            except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{provider.name}: {exc}")
                _log_call(
                    db,
                    provider=provider.name,
                    model=provider.model,
                    purpose=purpose,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=0,
                    cost_usd=Decimal("0"),
                    duration_ms=int((time.monotonic() - started) * 1000),
                    status="failed",
                    error=str(exc)[:1000],
                    error_type=_classify_error(exc),
                    raw_response=content if "content" in locals() else None,
                )

        raise LlmFailed("; ".join(errors) or "LLM providers failed")
    except SystemActionBlocked as exc:
        _log_blocked(db, purpose, prompt_tokens, "kill_switch", started, exc)
        raise LlmBlocked(str(exc)) from exc
    except LlmBlocked as exc:
        _log_blocked(db, purpose, prompt_tokens, "blocked", started, exc)
        raise


def _providers(reverse: bool = False) -> list[Provider]:
    primary = os.getenv("HYDRA_LLM_PRIMARY", "anthropic").lower()
    fallback = os.getenv("HYDRA_LLM_FALLBACK", "openai").lower()
    order = []
    for name in (primary, fallback):
        if name and name not in order:
            order.append(name)

    providers: list[Provider] = []
    for name in order:
        if name == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
            providers.append(Provider("anthropic", ANTHROPIC_MODEL, os.environ["ANTHROPIC_API_KEY"]))
        if name == "openai" and os.getenv("OPENAI_API_KEY"):
            providers.append(Provider("openai", OPENAI_MODEL, os.environ["OPENAI_API_KEY"]))
    return providers[::-1] if reverse else providers


def _call_provider(
    provider: Provider,
    system_prompt: str,
    user_prompt: str,
    schema_hint: dict,
    max_tokens: int,
    timeout_seconds: int,
) -> tuple[str, dict[str, int]]:
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            if provider.name == "anthropic":
                return _call_anthropic(provider, system_prompt, user_prompt, schema_hint, max_tokens, timeout_seconds)
            if provider.name == "openai":
                return _call_openai(provider, system_prompt, user_prompt, schema_hint, max_tokens, timeout_seconds)
            raise ValueError(f"Unsupported provider {provider.name}")
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if 400 <= status < 500:
                raise
            last_exc = exc
        except httpx.HTTPError as exc:
            last_exc = exc
        if attempt == 0:
            time.sleep(0.25)
    if last_exc:
        raise last_exc
    raise LlmFailed("Provider call failed")


def _call_anthropic(
    provider: Provider,
    system_prompt: str,
    user_prompt: str,
    schema_hint: dict,
    max_tokens: int,
    timeout_seconds: int,
) -> tuple[str, dict[str, int]]:
    payload = {
        "model": provider.model,
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": _json_only_user_prompt(user_prompt, schema_hint),
            }
        ],
    }
    headers = {
        "x-api-key": provider.api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
    usage = data.get("usage", {})
    return text.strip(), {
        "prompt_tokens": int(usage.get("input_tokens") or 0),
        "completion_tokens": int(usage.get("output_tokens") or 0),
    }


def _call_openai(
    provider: Provider,
    system_prompt: str,
    user_prompt: str,
    schema_hint: dict,
    max_tokens: int,
    timeout_seconds: int,
) -> tuple[str, dict[str, int]]:
    payload = {
        "model": provider.model,
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": _json_only_user_prompt(user_prompt, schema_hint),
            },
        ],
    }
    headers = {"authorization": f"Bearer {provider.api_key}", "content-type": "application/json"}
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    choice = data.get("choices", [{}])[0]
    content = choice.get("message", {}).get("content", "")
    usage = data.get("usage", {})
    return content.strip(), {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
    }


def _get_daily_budget(db) -> Decimal:
    flag = db.get(SystemFlag, "daily_budget_usd")
    try:
        return Decimal(flag.value if flag else "3")
    except Exception:
        return Decimal("3")


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 4) + 1)


def _completion_budget_for(purpose: str) -> int:
    if purpose == "hn_classification":
        return 180
    if purpose == "product_prefill":
        return 360
    if purpose == "outline":
        return 1200
    if purpose == "product_content":
        return 3500
    if purpose == "listing_copy":
        return 2200
    if purpose == "qa_review":
        return 1400
    if purpose == "distribution_post":
        return 2000
    if purpose in ("market_pattern_extraction", "market_opportunity_generation"):
        return 1600
    return 300


def _json_only_user_prompt(user_prompt: str, schema_hint: dict) -> str:
    return (
        f"{user_prompt}\n\n"
        "Return exactly one valid JSON object matching this schema hint.\n"
        "Do not wrap it in markdown fences. Do not include prose before or after the object.\n"
        "Escape newlines inside string values as \\n. Escape double quotes inside string values.\n"
        "Finish all strings, arrays, and objects before stopping.\n"
        f"Schema hint:\n{json.dumps(schema_hint, ensure_ascii=True)}"
    )


def _parse_json_object(content: str) -> dict:
    """Parse provider JSON while tolerating common model wrappers.

    This deliberately stays conservative: it accepts valid JSON, markdown-fenced
    JSON, or the first complete JSON object embedded in prose. It then performs
    one local repair pass for common formatting defects, such as literal newlines
    inside strings and trailing commas. Truncated JSON still fails.
    """
    candidates = [
        content,
        _strip_markdown_fence(content),
        _extract_json_object_text(content),
    ]

    first_error: Exception | None = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return _loads_json_object(candidate)
        except (json.JSONDecodeError, ValueError) as exc:
            first_error = first_error or exc

    repaired = _repair_json_text(_extract_json_object_text(content) or _strip_markdown_fence(content))
    if repaired:
        try:
            return _loads_json_object(repaired)
        except (json.JSONDecodeError, ValueError) as exc:
            first_error = first_error or exc

    raise ValueError(str(first_error or "No JSON object found"))


def _loads_json_object(text: str) -> dict:
    data = json.loads(text.strip())
    if not isinstance(data, dict):
        raise ValueError("JSON response was not an object")
    return data


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```(?:json|JSON)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    return match.group(1).strip() if match else stripped


def _extract_json_object_text(text: str) -> str | None:
    cleaned = _strip_markdown_fence(text)
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            obj, end = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return cleaned[index : index + end].strip()
    return _balanced_object_slice(cleaned)


def _balanced_object_slice(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1].strip()
    return None


def _repair_json_text(text: str | None) -> str | None:
    if not text:
        return None
    text = _strip_markdown_fence(text)
    text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return _escape_control_chars_inside_strings(text)


def _escape_control_chars_inside_strings(text: str) -> str:
    output: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                output.append(char)
                escaped = False
                continue
            if char == "\\":
                output.append(char)
                escaped = True
                continue
            if char == '"':
                in_string = False
                output.append(char)
                continue
            if char == "\n":
                output.append("\\n")
                continue
            if char == "\r":
                output.append("\\n")
                continue
            if char == "\t":
                output.append("\\t")
                continue
            output.append(char)
            continue
        if char == '"':
            in_string = True
        output.append(char)
    return "".join(output)


def _format_json_parse_error(exc: Exception, content: str) -> str:
    preview = (content or "").replace("\n", "\\n")[:500]
    return (
        f"Invalid JSON from provider after cleanup/repair: {exc}. "
        f"Raw output logged for debugging. Preview: {preview}"
    )


def _estimate_cost(provider: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    pricing = PRICING.get(provider, PRICING["anthropic"])
    return (
        Decimal(prompt_tokens) * pricing["input"]
        + Decimal(completion_tokens) * pricing["output"]
    ).quantize(Decimal("0.000001"))


def _classify_error(exc: Exception) -> str:
    """Return a short error type label for operator visibility.

    Labels:
      auth_error     — bad API key, 401
      quota_error    — rate limit or billing, 429
      bad_request    — bad model name or invalid params, 400
      provider_5xx   — provider server error, 5xx
      timeout        — request timed out
      bad_json       — response not valid JSON or not an object
      kill_switch    — hydra:kill flag active
      budget_exceeded— daily or per-call budget exceeded
      missing_key    — no API key configured
      unknown        — anything else
    """
    msg = str(exc).lower()
    # httpx HTTP status errors — check status code first
    if hasattr(exc, "response"):
        status = getattr(exc.response, "status_code", 0)
        if status == 401:
            return "auth_error"
        if status == 429:
            return "quota_error"
        if status == 400:
            return "bad_request"
        if 500 <= status < 600:
            return "provider_5xx"
    # Exception type checks
    if isinstance(exc, (json.JSONDecodeError, ValueError)) and (
        "json" in msg or "not an object" in msg or "valid" in msg
    ):
        return "bad_json"
    if "timeout" in msg or "timed out" in type(exc).__name__.lower():
        return "timeout"
    # String pattern checks for wrapped/re-raised messages
    if any(w in msg for w in ("401", "authentication", "auth", "api key", "invalid_api_key", "x-api-key")):
        return "auth_error"
    if any(w in msg for w in ("429", "rate_limit", "rate limit", "quota", "billing", "insufficient")):
        return "quota_error"
    if any(w in msg for w in ("400", "bad request", "invalid model", "model not found")):
        return "bad_request"
    if any(w in msg for w in ("500", "502", "503", "504", "server error", "provider")):
        return "provider_5xx"
    if "timeout" in msg:
        return "timeout"
    if any(w in msg for w in ("json", "not an object", "decode", "unterminated string", "expecting value")):
        return "bad_json"
    if "kill switch" in msg:
        return "kill_switch"
    if any(w in msg for w in ("budget", "cap exceeded", "budget exceeded")):
        return "budget_exceeded"
    if any(w in msg for w in ("no llm api key", "no api key", "missing key")):
        return "missing_key"
    return "unknown"


def _log_blocked(db, purpose: str, prompt_tokens: int, status: str, started: float, exc: Exception) -> None:
    # Determine specific blocked type
    msg = str(exc).lower()
    if "kill switch" in msg:
        error_type = "kill_switch"
    elif "budget" in msg or "cap" in msg:
        error_type = "budget_exceeded"
    elif "no llm api key" in msg or "no api key" in msg:
        error_type = "missing_key"
    else:
        error_type = "blocked"
    _log_call(
        db,
        provider=None,
        model=None,
        purpose=purpose,
        prompt_tokens=prompt_tokens,
        completion_tokens=0,
        cost_usd=Decimal("0"),
        duration_ms=int((time.monotonic() - started) * 1000),
        status=status,
        error=str(exc)[:1000],
        error_type=error_type,
    )


def _log_call(
    db,
    provider: str | None,
    model: str | None,
    purpose: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: Decimal,
    duration_ms: int,
    status: str,
    error: str | None,
    error_type: str | None = None,
    raw_response: str | None = None,
) -> None:
    db.add(
        LlmCall(
            provider=provider,
            model=model,
            purpose=purpose,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            status=status,
            error=error,
            error_type=error_type,
            raw_response=raw_response[:12000] if raw_response else None,
        )
    )
    db.flush()
