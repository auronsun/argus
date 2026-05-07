"""User-supplied API keys and model overrides, stored in a local JSON file.

Stored on disk at `<cache>/secrets.json` with mode 0600. The file is gitignored.
Key values are NEVER returned over the API — the settings route only reports
which slots are populated and what model is effective.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from ..config import get_settings


# Provider key/host slots
LLM_KEY_SLOTS = ("anthropic", "openai", "deepseek", "qwen", "nvidia", "ollama_host")

# Model-name slots (one per LLM provider)
LLM_MODEL_SLOTS = (
    "anthropic_model", "openai_model", "deepseek_model",
    "qwen_model", "nvidia_model", "ollama_model",
)

# Premium data-source slots
DATA_SLOTS = ("alpha_vantage", "finnhub", "tushare", "longbridge_token")

ALL_SLOTS = LLM_KEY_SLOTS + LLM_MODEL_SLOTS + DATA_SLOTS

# Provider -> (key_slot, model_slot, env_default_field_for_model)
LLM_PROVIDERS: dict[str, tuple[str, str, str]] = {
    "anthropic": ("anthropic", "anthropic_model", "anthropic_model"),
    "openai":    ("openai",    "openai_model",   "openai_model"),
    "deepseek":  ("deepseek",  "deepseek_model", "deepseek_model"),
    "qwen":      ("qwen",      "qwen_model",     "qwen_model"),
    "nvidia":    ("nvidia",    "nvidia_model",   "nvidia_model"),
    "ollama":    ("ollama_host", "ollama_model", "ollama_model"),
}

_lock = threading.Lock()


def _path() -> Path:
    return get_settings().cache_dir / "secrets.json"


def _read() -> dict[str, str]:
    p = _path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text("utf-8")) or {}
    except json.JSONDecodeError:
        return {}


def _write(data: dict[str, str]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(p)


def get_all() -> dict[str, str]:
    with _lock:
        return _read()


def get(slot: str) -> str:
    return get_all().get(slot, "")


def set_many(updates: dict[str, str]) -> None:
    with _lock:
        data = _read()
        for k, v in updates.items():
            if k not in ALL_SLOTS:
                continue
            v = (v or "").strip()
            if v:
                data[k] = v
            else:
                data.pop(k, None)
        _write(data)


def clear(slot: str) -> None:
    with _lock:
        data = _read()
        data.pop(slot, None)
        _write(data)


def effective(slot: str, env_value: str = "") -> str:
    """UI-stored value takes precedence over the corresponding env value."""
    val = get(slot)
    return val or (env_value or "")


def effective_model(provider: str) -> str:
    """Resolve the effective model name for an LLM provider (UI > env > built-in)."""
    if provider not in LLM_PROVIDERS:
        return ""
    _, model_slot, env_field = LLM_PROVIDERS[provider]
    s = get_settings()
    env_val = getattr(s, env_field, "")
    return effective(model_slot, env_val)


def merged_view() -> dict[str, Any]:
    """A view of (env, ui) provenance for keys + the effective model per LLM."""
    s = get_settings()
    data = get_all()

    def key_entry(slot: str, env_val: str) -> dict[str, Any]:
        ui_val = data.get(slot)
        return {
            "configured": bool(ui_val or env_val),
            "source": "ui" if ui_val else ("env" if env_val else None),
        }

    def llm_entry(provider: str, key_slot: str, env_key: str, model_slot: str, env_model: str) -> dict[str, Any]:
        ui_key = data.get(key_slot)
        ui_model = data.get(model_slot)
        return {
            "configured": bool(ui_key or env_key),
            "source": "ui" if ui_key else ("env" if env_key else None),
            "model": ui_model or env_model,
            "model_source": "ui" if ui_model else ("env" if env_model else None),
        }

    return {
        # LLM providers — include effective model
        "anthropic": llm_entry("anthropic", "anthropic", s.anthropic_api_key, "anthropic_model", s.anthropic_model),
        "openai":    llm_entry("openai",    "openai",    s.openai_api_key,    "openai_model",    s.openai_model),
        "deepseek":  llm_entry("deepseek",  "deepseek",  s.deepseek_api_key,  "deepseek_model",  s.deepseek_model),
        "qwen":      llm_entry("qwen",      "qwen",      s.qwen_api_key,      "qwen_model",      s.qwen_model),
        "nvidia":    llm_entry("nvidia",    "nvidia",    s.nvidia_api_key,    "nvidia_model",    s.nvidia_model),
        "ollama_host": llm_entry("ollama",  "ollama_host", s.ollama_host,    "ollama_model",    s.ollama_model),

        # Data sources — keys only
        "alpha_vantage":    key_entry("alpha_vantage",    s.alpha_vantage_api_key),
        "finnhub":          key_entry("finnhub",          s.finnhub_api_key),
        "tushare":          key_entry("tushare",          s.tushare_token),
        "longbridge_token": key_entry("longbridge_token", s.longbridge_access_token),
    }
