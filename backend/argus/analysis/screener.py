"""Cross-market screener — filters a candidate universe by simple criteria."""
from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from ..markets import MARKETS, get_adapter
from ..markets.base import Market, Quote
from ..utils import logger
from .indicators import compute_indicators


class ScreenerCriteria(BaseModel):
    markets: list[Market] = Field(default_factory=lambda: list(MARKETS))
    symbols: list[str] = Field(default_factory=list, max_length=200)
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    min_change_pct: float | None = Field(default=None, ge=-100, le=100)
    max_change_pct: float | None = Field(default=None, ge=-100, le=100)
    min_market_cap: float | None = Field(default=None, ge=0)
    rsi_below: float | None = Field(default=None, ge=0, le=100)
    rsi_above: float | None = Field(default=None, ge=0, le=100)
    require_golden_cross: bool = False
    limit: int = Field(default=50, ge=1, le=200)
    concurrency: int = Field(default=8, ge=1, le=32)


# Built-in starter universes — kept small so the screener is responsive.
_DEFAULT_UNIVERSE: dict[Market, list[str]] = {
    "US": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO",
        "JPM", "V", "WMT", "XOM", "JNJ", "PG", "MA", "HD",
        "COST", "ORCL", "AMD", "NFLX", "CRM", "ADBE", "PEP", "KO",
    ],
    "CN": [
        "600519", "601318", "600036", "000858", "000333", "002594",
        "300750", "601012", "002475", "600276", "000001", "601166",
        "601398", "600028", "601899", "600030",
    ],
    "HK": [
        "0700", "9988", "1810", "3690", "0388", "0005",
        "0941", "1299", "2318", "9618", "1024", "0883",
        "1398", "3968", "0011",
    ],
}


async def _enrich(symbol: str, market: Market, sem: asyncio.Semaphore) -> dict[str, Any] | None:
    adapter = get_adapter(market)
    async with sem:
        try:
            quote = await adapter.quote(symbol)
            candles = await adapter.history(symbol, interval="1d")
        except Exception as e:
            logger.warning(f"screener enrich failed for {market}:{symbol}: {e}")
            return None
    ind = compute_indicators(candles[-260:]) if candles else {"latest": {}}
    latest = ind.get("latest") or {}
    return {
        "symbol": quote.symbol,
        "name": quote.name,
        "market": market,
        "price": quote.price,
        "change_pct": quote.change_pct,
        "market_cap": quote.market_cap,
        "currency": quote.currency,
        "rsi_14": latest.get("rsi_14"),
        "sma_50": latest.get("sma_50"),
        "sma_200": latest.get("sma_200"),
        "macd": latest.get("macd"),
        "macd_signal": latest.get("macd_signal"),
    }


def _passes(row: dict[str, Any], c: ScreenerCriteria) -> bool:
    if c.min_price is not None and (row["price"] or 0) < c.min_price:
        return False
    if c.max_price is not None and (row["price"] or 0) > c.max_price:
        return False
    if c.min_change_pct is not None and (row["change_pct"] or 0) < c.min_change_pct:
        return False
    if c.max_change_pct is not None and (row["change_pct"] or 0) > c.max_change_pct:
        return False
    if c.min_market_cap is not None and (row.get("market_cap") or 0) < c.min_market_cap:
        return False
    if c.rsi_below is not None and (row.get("rsi_14") is None or row["rsi_14"] >= c.rsi_below):
        return False
    if c.rsi_above is not None and (row.get("rsi_14") is None or row["rsi_14"] <= c.rsi_above):
        return False
    if c.require_golden_cross:
        s50, s200 = row.get("sma_50"), row.get("sma_200")
        if not (s50 and s200 and s50 > s200):
            return False
    return True


async def run_screener(criteria: ScreenerCriteria) -> list[dict[str, Any]]:
    if criteria.symbols:
        pairs: list[tuple[str, Market]] = []
        for sym in criteria.symbols:
            from ..markets.registry import detect_market
            pairs.append((sym, detect_market(sym)))
    else:
        pairs = []
        for m in criteria.markets:
            for sym in _DEFAULT_UNIVERSE.get(m, []):
                pairs.append((sym, m))

    sem = asyncio.Semaphore(max(1, criteria.concurrency))
    rows = await asyncio.gather(*(_enrich(s, m, sem) for s, m in pairs))
    rows = [r for r in rows if r is not None]
    rows = [r for r in rows if _passes(r, criteria)]
    rows.sort(key=lambda r: (r.get("change_pct") or 0), reverse=True)
    return rows[: criteria.limit]
