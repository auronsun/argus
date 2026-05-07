"""LLM provider abstraction. The same client interface across Anthropic / OpenAI /
DeepSeek / Qwen (DashScope) / Ollama, picked from environment.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator, Iterable

import httpx

from ..config import get_settings
from ..utils import logger


@dataclass
class Message:
    role: str  # 'system' | 'user' | 'assistant'
    content: str


class LLMClient:
    """Streaming-only chat interface.

    Each provider implements `astream()` which yields text deltas.
    `acomplete()` is sugar that joins them.
    """

    provider: str
    model: str

    async def astream(self, messages: list[Message]) -> AsyncIterator[str]:
        raise NotImplementedError

    async def acomplete(self, messages: list[Message]) -> str:
        chunks: list[str] = []
        async for d in self.astream(messages):
            chunks.append(d)
        return "".join(chunks)


# ----------------------------------------------------------------------------
# Anthropic
# ----------------------------------------------------------------------------
class AnthropicClient(LLMClient):
    provider = "anthropic"

    def __init__(self, api_key: str, model: str, base_url: str = ""):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def astream(self, messages: list[Message]) -> AsyncIterator[str]:
        from anthropic import AsyncAnthropic  # lazy import

        kwargs: dict[str, str] = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = AsyncAnthropic(**kwargs)
        sys = next((m.content for m in messages if m.role == "system"), "")
        body = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        async with client.messages.stream(
            model=self.model,
            max_tokens=2048,
            system=sys,
            messages=body,
        ) as stream:
            async for text in stream.text_stream:
                yield text


# ----------------------------------------------------------------------------
# OpenAI-compatible (OpenAI, DeepSeek, Qwen)
# ----------------------------------------------------------------------------
class OpenAICompatClient(LLMClient):
    def __init__(self, provider: str, api_key: str, model: str, base_url: str | None = None):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def astream(self, messages: list[Message]) -> AsyncIterator[str]:
        from openai import AsyncOpenAI  # lazy import

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url) if self.base_url else AsyncOpenAI(api_key=self.api_key)
        body = [{"role": m.role, "content": m.content} for m in messages]
        stream = await client.chat.completions.create(
            model=self.model,
            messages=body,
            stream=True,
            temperature=0.7,
            max_tokens=2048,
        )
        async for event in stream:
            choice = event.choices[0] if event.choices else None
            if not choice:
                continue
            delta = choice.delta.content or ""
            if delta:
                yield delta


# ----------------------------------------------------------------------------
# Ollama (local)
# ----------------------------------------------------------------------------
class OllamaClient(LLMClient):
    provider = "ollama"

    def __init__(self, host: str, model: str):
        self.host = host.rstrip("/")
        self.model = model

    async def astream(self, messages: list[Message]) -> AsyncIterator[str]:
        body = [{"role": m.role, "content": m.content} for m in messages]
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=300.0)) as client:
            async with client.stream(
                "POST",
                f"{self.host}/api/chat",
                json={"model": self.model, "messages": body, "stream": True},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    delta = (chunk.get("message") or {}).get("content", "")
                    if delta:
                        yield delta


# ----------------------------------------------------------------------------
# Mock (no key configured) — yields a deterministic templated response
# ----------------------------------------------------------------------------
class MockClient(LLMClient):
    provider = "mock"
    model = "argus-mock-1"

    async def astream(self, messages: list[Message]) -> AsyncIterator[str]:
        last = messages[-1].content if messages else ""
        canned = (
            "[Demo mode — no LLM API key detected]\n\n"
            "I'm Argus's mock analyst. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, "
            "DEEPSEEK_API_KEY, or QWEN_API_KEY in `.env` to enable live analysis.\n\n"
            f"Prompt summary: {last[:160]}…"
        )
        for chunk in _split_for_streaming(canned, 14):
            yield chunk
            await asyncio.sleep(0.04)


def _split_for_streaming(text: str, size: int) -> Iterable[str]:
    for i in range(0, len(text), size):
        yield text[i : i + size]


# ----------------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------------
def _resolve_primary() -> tuple[str, str, str] | None:
    """Resolve the active LLM at call-time. UI-stored secrets override env.

    Priority: anthropic > openai > deepseek > qwen > nvidia > ollama (local).
    The model name is also UI-overridable via secrets.
    """
    from ..storage import secrets  # local to avoid import cycle

    s = get_settings()
    candidates = [
        ("anthropic", secrets.effective("anthropic", s.anthropic_api_key), secrets.effective_model("anthropic")),
        ("openai",    secrets.effective("openai",    s.openai_api_key),    secrets.effective_model("openai")),
        ("deepseek",  secrets.effective("deepseek",  s.deepseek_api_key),  secrets.effective_model("deepseek")),
        ("qwen",      secrets.effective("qwen",      s.qwen_api_key),      secrets.effective_model("qwen")),
        ("nvidia",    secrets.effective("nvidia",    s.nvidia_api_key),    secrets.effective_model("nvidia")),
    ]
    for provider, key, model in candidates:
        if key:
            return provider, key, model
    host = secrets.effective("ollama_host", s.ollama_host)
    if host:
        return "ollama", host, secrets.effective_model("ollama")
    return None


def get_llm() -> LLMClient:
    chosen = _resolve_primary()
    if chosen is None:
        logger.info("No LLM key configured — using MockClient")
        return MockClient()
    provider, key, model = chosen
    s = get_settings()
    if provider == "anthropic":
        return AnthropicClient(api_key=key, model=model, base_url=s.anthropic_base_url)
    if provider == "openai":
        return OpenAICompatClient("openai", api_key=key, model=model)
    if provider == "deepseek":
        return OpenAICompatClient(
            "deepseek", api_key=key, model=model, base_url="https://api.deepseek.com/v1"
        )
    if provider == "qwen":
        return OpenAICompatClient(
            "qwen", api_key=key, model=model,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    if provider == "nvidia":
        return OpenAICompatClient(
            "nvidia", api_key=key, model=model,
            base_url=(s.nvidia_base_url or "https://integrate.api.nvidia.com/v1"),
        )
    if provider == "ollama":
        return OllamaClient(host=key, model=model)
    return MockClient()
