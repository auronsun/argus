"""Lightweight smoke tests — no network, no external services."""
from __future__ import annotations

from datetime import datetime

from argus.analysis.indicators import compute_indicators, latest_signals
from argus.markets import detect_market
from argus.markets.base import Candle


def _fake_candles(n: int = 250):
    out = []
    price = 100.0
    for i in range(n):
        price = price * (1 + (0.01 if i % 3 == 0 else -0.005))
        out.append(Candle(time=datetime(2024, 1, 1), open=price, high=price * 1.01, low=price * 0.99, close=price, volume=1_000_000))
    return out


def test_market_detection():
    assert detect_market("AAPL") == "US"
    assert detect_market("600519") == "CN"
    assert detect_market("600519.SH") == "CN"
    assert detect_market("0700.HK") == "HK"


def test_indicators_compute():
    ind = compute_indicators(_fake_candles())
    assert ind["latest"] is not None
    sigs = latest_signals(ind)
    assert isinstance(sigs, dict)


def test_indicators_empty_input():
    """Should not crash on no data and should return an empty shape."""
    out = compute_indicators([])
    assert out["latest"] == {}
    assert out["series"] == []
    assert latest_signals(out) == {}


def test_indicators_short_input_does_not_crash():
    """Fewer than 14 bars: rolling windows produce NaN, which we replace with None."""
    candles = _fake_candles(n=5)
    out = compute_indicators(candles)
    # Latest row exists; rolling-window indicators are None until enough history.
    assert out["latest"]["rsi_14"] is None
    assert out["latest"]["sma_50"] is None
