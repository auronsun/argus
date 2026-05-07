"""Hermetic tests for the flow aggregator. No network."""
from __future__ import annotations

import pytest

from argus.analysis import flow as flow_mod
from argus.analysis.flow import FlowSignals, aggregate_flow
from argus.storage import secrets


@pytest.fixture(autouse=True)
def _clear_flow_cache():
    flow_mod._cache.invalidate()
    yield
    flow_mod._cache.invalidate()


@pytest.mark.asyncio
async def test_us_no_finnhub_key_degrades_gracefully(monkeypatch):
    """No Finnhub key → no insider data, but yfinance short interest is also
    isolated (we monkeypatch yfinance to avoid a real network call)."""
    secrets.clear("finnhub")

    # Patch yfinance.Ticker.info with a fake — short interest fields stay empty.
    class _FakeTicker:
        info = {"sharesShort": 1_000_000, "floatShares": 100_000_000, "shortRatio": 2.5}
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", lambda sym: _FakeTicker())

    out = await aggregate_flow("AAPL", "US")
    assert isinstance(out, FlowSignals)
    assert out.market == "US"
    assert out.symbol == "AAPL"
    assert out.insider_transactions == []
    # yfinance short stats still come through
    assert out.short_pct_float == pytest.approx(1.0, rel=0.01)
    assert out.short_ratio_dtc == 2.5
    # We tell the user explicitly when we couldn't get insider data
    assert any("insider" in n.lower() for n in out.notes)


@pytest.mark.asyncio
async def test_cn_failures_are_isolated(monkeypatch):
    """Each CN sub-fetch is wrapped in to_thread + return_exceptions, so one
    failing source shouldn't take the others down."""
    monkeypatch.setattr(flow_mod, "_cn_lhb_recent",
                        lambda code: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(flow_mod, "_cn_northbound_5d", lambda code: 1234567.0)
    monkeypatch.setattr(flow_mod, "_cn_margin_5d_change", lambda code: -2.5)

    out = await aggregate_flow("600519", "CN")
    assert out.lhb_recent == []
    assert any("龙虎榜" in n for n in out.notes)
    assert out.northbound_5d_net_cny == 1234567.0
    assert out.margin_balance_5d_change_pct == -2.5


@pytest.mark.asyncio
async def test_hk_returns_placeholder():
    """HK isn't wired in v1 — must still return a FlowSignals, with a clear note."""
    out = await aggregate_flow("0700.HK", "HK")
    assert out.market == "HK"
    assert out.lhb_recent == []
    assert out.short_pct_float is None
    assert any("HK flow" in n for n in out.notes)


@pytest.mark.asyncio
async def test_aggregate_caches_per_key(monkeypatch):
    """Two calls for the same (symbol, market) hit the cache — only one fetch."""
    calls = {"n": 0}

    async def fake(symbol, market):
        calls["n"] += 1
        return FlowSignals(market=market, symbol=symbol)

    monkeypatch.setattr(flow_mod, "_fetch", fake)

    a = await aggregate_flow("AAPL", "US")
    b = await aggregate_flow("AAPL", "US")
    assert a.symbol == b.symbol == "AAPL"
    assert calls["n"] == 1
