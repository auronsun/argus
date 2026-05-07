"""Resolve a user-typed symbol to the correct market adapter."""
from __future__ import annotations

import re
import asyncio

from .base import Market, MarketAdapter, SymbolSearchResult
from .cn import CNAdapter
from .hk import HKAdapter
from .us import USAdapter


_ADAPTERS: dict[Market, MarketAdapter] = {
    "US": USAdapter(),
    "CN": CNAdapter(),
    "HK": HKAdapter(),
}

MARKETS: list[Market] = ["US", "CN", "HK"]


def detect_market(symbol: str) -> Market:
    """Best-effort market detection from a raw user-typed symbol."""
    s = symbol.strip().upper()
    if s.endswith(".HK") or re.fullmatch(r"\d{4,5}", s):
        # Pure 4-5 digit codes are ambiguous (could be HK or CN); prefer HK only with .HK suffix
        if s.endswith(".HK"):
            return "HK"
    if re.search(r"\.(SH|SS|SZ|BJ)$", s):
        return "CN"
    if s.isdigit() and len(s) == 6:
        return "CN"
    if s.isdigit() and len(s) <= 5:
        return "HK"
    return "US"


def get_adapter(market_or_symbol: str) -> MarketAdapter:
    s = market_or_symbol.upper()
    if s in _ADAPTERS:
        return _ADAPTERS[s]  # type: ignore[index]
    return _ADAPTERS[detect_market(s)]


async def search_symbols(query: str, limit: int = 8) -> list[SymbolSearchResult]:
    """Fan out to every adapter, with a per-adapter timeout so one slow
    upstream (yfinance.Search, akshare boards) can't drag down the rest.

    The HK and CN adapters are now O(1) curated-list lookups, so the
    timeout matters mostly as a safety net for the US adapter, which
    still hits Yahoo's search API.
    """
    PER_ADAPTER_TIMEOUT = 5.0

    async def _safe(market: Market) -> list[SymbolSearchResult]:
        try:
            return await asyncio.wait_for(
                _ADAPTERS[market].search(query, limit=limit),
                timeout=PER_ADAPTER_TIMEOUT,
            )
        except asyncio.TimeoutError:
            from ..utils import logger
            logger.warning(f"search timeout for {market} on query='{query[:30]}'")
            return []
        except Exception as e:
            from ..utils import logger
            logger.warning(f"search error for {market}: {e}")
            return []

    results = await asyncio.gather(*(_safe(m) for m in MARKETS))
    out: list[SymbolSearchResult] = []
    for r in results:
        out.extend(r)

    # Stable de-dup by symbol
    seen: set[str] = set()
    uniq: list[SymbolSearchResult] = []
    for r in out:
        if r.symbol in seen:
            continue
        seen.add(r.symbol)
        uniq.append(r)
    return uniq[: limit * 2]
