"""Smoke tests for configured LLM providers.

Used by the Settings UI: after the user pastes a key, they can click
"Test" and we send a tiny, single-token-budget prompt to the provider to
verify the key + model + base URL all work together. Errors are
classified into stable buckets the frontend can show as friendly chips.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from ..config import get_settings
from ..storage import secrets
from .llm import (
    AnthropicClient,
    LLMClient,
    Message,
    OllamaClient,
    OpenAICompatClient,
)


# Slots the UI can test. Maps the secret-slot name (what the UI sends)
# to a normalised provider name used internally.
SLOT_TO_PROVIDER: dict[str, str] = {
    "anthropic":   "anthropic",
    "openai":      "openai",
    "deepseek":    "deepseek",
    "qwen":        "qwen",
    "nvidia":      "nvidia",
    "ollama_host": "ollama",
}


def build_llm_for(provider: str) -> Optional[LLMClient]:
    """Build an LLMClient for a SPECIFIC provider, regardless of priority.

    Returns None if the key/host for that provider isn't configured.
    """
    s = get_settings()
    if provider == "anthropic":
        key = secrets.effective("anthropic", s.anthropic_api_key)
        model = secrets.effective_model("anthropic")
        if not key:
            return None
        return AnthropicClient(api_key=key, model=model, base_url=s.anthropic_base_url)
    if provider == "openai":
        key = secrets.effective("openai", s.openai_api_key)
        model = secrets.effective_model("openai")
        if not key:
            return None
        return OpenAICompatClient("openai", api_key=key, model=model)
    if provider == "deepseek":
        key = secrets.effective("deepseek", s.deepseek_api_key)
        model = secrets.effective_model("deepseek")
        if not key:
            return None
        return OpenAICompatClient(
            "deepseek", api_key=key, model=model, base_url="https://api.deepseek.com/v1"
        )
    if provider == "qwen":
        key = secrets.effective("qwen", s.qwen_api_key)
        model = secrets.effective_model("qwen")
        if not key:
            return None
        return OpenAICompatClient(
            "qwen", api_key=key, model=model,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    if provider == "nvidia":
        key = secrets.effective("nvidia", s.nvidia_api_key)
        model = secrets.effective_model("nvidia")
        if not key:
            return None
        return OpenAICompatClient(
            "nvidia", api_key=key, model=model,
            base_url=(s.nvidia_base_url or "https://integrate.api.nvidia.com/v1"),
        )
    if provider == "ollama":
        host = secrets.effective("ollama_host", s.ollama_host)
        model = secrets.effective_model("ollama")
        if not host:
            return None
        return OllamaClient(host=host, model=model)
    return None


def _truncate(s: str, n: int = 220) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _classify(e: Exception) -> tuple[str, str]:
    """Map an upstream error to a stable kind + a short displayable detail."""
    msg = str(e)
    low = msg.lower()
    name = e.__class__.__name__.lower()

    if "401" in msg or "unauthorized" in low or "invalid_api_key" in low or "authentication" in low:
        return "auth", _truncate(msg)
    if "403" in msg or "forbidden" in low or "permission" in low:
        return "auth", _truncate(msg)
    if (
        "404" in msg
        or "model_not_found" in low
        or ("model" in low and ("not found" in low or "does not exist" in low or "no model" in low))
    ):
        return "model_not_found", _truncate(msg)
    if "429" in msg or "rate_limit" in low or "rate limit" in low or "quota" in low or "insufficient" in low:
        return "rate_limit", _truncate(msg)
    if (
        "connecterror" in name
        or "connecttimeout" in name
        or "readtimeout" in name
        or "timeout" in low
        or "name or service not known" in low
        or "dns" in low
        or "nameresolutionerror" in name
    ):
        return "network", _truncate(msg)
    return "unknown", _truncate(msg)


async def smoke_test_llm(provider: str, timeout: float = 20.0) -> dict[str, Any]:
    """Send a tiny prompt; return a structured result.

    Successful shape:
        {ok: true, kind: "ok", latency_ms, model, provider, sample}
    Failure shape:
        {ok: false, kind: "no_key"|"auth"|"model_not_found"|"rate_limit"|"network"|"timeout"|"unknown",
         detail, model?, provider}
    """
    client = build_llm_for(provider)
    if client is None:
        return {"ok": False, "kind": "no_key", "provider": provider,
                "detail": "Key not configured for this provider."}

    msg = Message(role="user", content="Reply with the single word OK.")
    chunks: list[str] = []

    async def _go() -> None:
        async for delta in client.astream([msg]):
            chunks.append(delta)
            # Cap at ~30 chars — we just want any signal that the model responded.
            if sum(len(c) for c in chunks) >= 32:
                break

    started = time.monotonic()
    try:
        await asyncio.wait_for(_go(), timeout=timeout)
    except asyncio.TimeoutError:
        return {"ok": False, "kind": "timeout", "provider": provider, "model": client.model,
                "detail": f"No response within {int(timeout)}s."}
    except Exception as e:
        kind, detail = _classify(e)
        return {"ok": False, "kind": kind, "provider": provider, "model": client.model,
                "detail": detail}

    latency_ms = int((time.monotonic() - started) * 1000)
    sample = _truncate("".join(chunks), 120)
    return {"ok": True, "kind": "ok", "latency_ms": latency_ms,
            "provider": provider, "model": client.model, "sample": sample}
