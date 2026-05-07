"""Health + capability discovery."""
from __future__ import annotations

from fastapi import APIRouter

from .. import __version__
from ..agents.llm import _resolve_primary
from ..config import get_settings
from ..storage import secrets

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health")
def health():
    return {"ok": True, "version": __version__}


def _has(slot: str, env_val: str) -> bool:
    return bool(secrets.effective(slot, env_val))


@router.get("/capabilities")
def capabilities():
    s = get_settings()
    primary = _resolve_primary()
    return {
        "version": __version__,
        "llm": {
            "configured": primary is not None,
            "provider": primary[0] if primary else None,
            "model": primary[2] if primary else None,
            "available": {
                "anthropic": _has("anthropic", s.anthropic_api_key),
                "openai":    _has("openai",    s.openai_api_key),
                "deepseek":  _has("deepseek",  s.deepseek_api_key),
                "qwen":      _has("qwen",      s.qwen_api_key),
                "nvidia":    _has("nvidia",    s.nvidia_api_key),
                "ollama":    _has("ollama_host", s.ollama_host),
            },
        },
        "data": {
            "alpha_vantage": _has("alpha_vantage", s.alpha_vantage_api_key),
            "finnhub":       _has("finnhub",       s.finnhub_api_key),
            "tushare":       _has("tushare",       s.tushare_token),
            "longbridge":    _has("longbridge_token", s.longbridge_access_token),
        },
        "markets": ["US", "CN", "HK"],
    }
