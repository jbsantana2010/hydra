from __future__ import annotations

import json
import os
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
            try:
                content, usage = _call_provider(
                    provider,
                    system_prompt,
                    user_prompt,
                    schema_hint,
                    completion_tokens,
                    timeout_seconds,
                )
                data = json.loads(content)
                if not isinstance(data, dict):
                    raise ValueError("JSON response was not an object")
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
                "content": f"{user_prompt}\n\nReturn only JSON matching this schema hint:\n{json.dumps(schema_hint)}",
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
                "content": f"{user_prompt}\n\nReturn only JSON matching this schema hint:\n{json.dumps(schema_hint)}",
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
    return 300


def _estimate_cost(provider: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    pricing = PRICING.get(provider, PRICING["anthropic"])
    return (
        Decimal(prompt_tokens) * pricing["input"]
        + Decimal(completion_tokens) * pricing["output"]
    ).quantize(Decimal("0.000001"))


def _log_blocked(db, purpose: str, prompt_tokens: int, status: str, started: float, exc: Exception) -> None:
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
        )
    )
    db.flush()
