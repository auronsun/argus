"""Tests for the news aggregator's primary→Finnhub fallback. No real network."""
from __future__ import annotations

from typing import Any

import pytest

from argus.analysis import news as news_mod
from argus.storage import secrets


class _StubAdapter:
    """Minimal adapter stub for the aggregator. Returns whatever
    `news_payload` was set to on construction."""

    def __init__(self, news_payload: list[dict]):
        self._news_payload = news_payload

    def normalize(self, sym: str) -> str:
        return sym.upper()

    async def news(self, sym: str, limit: int = 10) -> list[dict]:
        return self._news_payload


@pytest.fixture(autouse=True)
def _clear_aggregator_cache():
    news_mod._cache.invalidate()
    secrets.clear("finnhub")
    yield
    news_mod._cache.invalidate()
    secrets.clear("finnhub")


@pytest.mark.asyncio
async def test_returns_primary_when_non_empty(monkeypatch):
    primary = [{"title": "real headline", "url": "x"}]
    monkeypatch.setattr(news_mod, "get_adapter", lambda *_: _StubAdapter(primary))
    out = await news_mod.aggregate_news("AAPL", "US", limit=5)
    assert out == primary


@pytest.mark.asyncio
async def test_skips_finnhub_when_no_key(monkeypatch):
    """Empty primary, no Finnhub key configured → return empty list,
    don't attempt the fallback HTTP call."""
    called: dict[str, bool] = {"finnhub": False}

    async def fake_finnhub(*a, **kw):
        called["finnhub"] = True
        return [{"title": "should not appear"}]

    monkeypatch.setattr(news_mod, "get_adapter", lambda *_: _StubAdapter([]))
    monkeypatch.setattr(news_mod, "_finnhub_company_news", fake_finnhub)

    out = await news_mod.aggregate_news("AAPL", "US", limit=5)
    assert out == []
    assert called["finnhub"] is False


@pytest.mark.asyncio
async def test_finnhub_fallback_fires_when_primary_empty(monkeypatch):
    primary: list[dict] = []
    fallback = [{"title": "from finnhub", "url": "y"}]

    async def fake_finnhub(symbol, key, limit):
        return fallback

    monkeypatch.setattr(news_mod, "get_adapter", lambda *_: _StubAdapter(primary))
    monkeypatch.setattr(news_mod, "_finnhub_company_news", fake_finnhub)
    secrets.set_many({"finnhub": "fnh-test-key"})

    out = await news_mod.aggregate_news("AAPL", "US", limit=5)
    assert out == fallback


@pytest.mark.asyncio
async def test_cn_never_uses_finnhub_fallback(monkeypatch):
    """Akshare is the canonical CN source; we don't want Finnhub for A-shares
    even if its key is set."""
    called: dict[str, Any] = {"finnhub": False}

    async def fake_finnhub(*a, **kw):
        called["finnhub"] = True
        return [{"title": "ng"}]

    monkeypatch.setattr(news_mod, "get_adapter", lambda *_: _StubAdapter([]))
    monkeypatch.setattr(news_mod, "_finnhub_company_news", fake_finnhub)
    secrets.set_many({"finnhub": "fnh-test-key"})

    out = await news_mod.aggregate_news("600519", "CN", limit=5)
    assert out == []
    assert called["finnhub"] is False


def test_finnhub_symbol_formatting():
    # US: passthrough
    assert news_mod._finnhub_symbol("AAPL", "US") == "AAPL"
    # HK: 5-digit internal → 4-digit Finnhub form
    assert news_mod._finnhub_symbol("00700.HK", "HK") == "0700.HK"
    # HK: shorter input still padded to 4
    assert news_mod._finnhub_symbol("700.HK", "HK") == "0700.HK"
