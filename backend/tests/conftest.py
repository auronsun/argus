"""Shared test fixtures.

The Settings tests touch the secrets store, which writes JSON inside
`<cache>/secrets.json`. We point the cache dir at a temp dir per session
so tests never mutate the user's real config.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure backend package is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def _isolate_argus_cache(tmp_path_factory):
    """Redirect Argus cache + DB into a throwaway dir AND blank out every
    real API-key env var, so tests don't pick up the user's .env values."""
    cache = tmp_path_factory.mktemp("argus-cache")
    db_path = tmp_path_factory.mktemp("argus-db") / "argus.sqlite"
    os.environ["ARGUS_CACHE_DIR"] = str(cache)
    os.environ["ARGUS_DB_PATH"] = str(db_path)

    # Force a clean baseline: empty every secret-style env var. Tests opt
    # into specific values via secrets.set_many() or monkeypatch.
    for var in [
        "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
        "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "QWEN_API_KEY",
        "NVIDIA_API_KEY", "OLLAMA_HOST",
        "POLYGON_API_KEY", "ALPHA_VANTAGE_API_KEY", "FINNHUB_API_KEY",
        "TUSHARE_TOKEN", "LONGBRIDGE_APP_KEY", "LONGBRIDGE_APP_SECRET",
        "LONGBRIDGE_ACCESS_TOKEN",
    ]:
        os.environ[var] = ""

    # Re-import and clear cached settings + DB engine so they pick up the new paths
    from argus.config import get_settings
    get_settings.cache_clear()
    import argus.storage.db as _db
    _db._engine = None
    _db.init_db()
    yield
