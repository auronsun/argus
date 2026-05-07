"""News aggregation with provider fallback.

For US / HK tickers, when the primary adapter (yfinance) returns no
news — which it often does for less-covered tickers — we fall back to
Finnhub's company-news endpoint if the user has a Finnhub key.

CN tickers stay with akshare (`stock_news_em`); Finnhub coverage of
mainland-China names is poor and akshare is generally fine.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx

from ..config import get_settings
from ..markets import get_adapter
from ..markets.base import Market
from ..storage import secrets
from ..utils import logger
from ..utils.cache import TTLCache


_FALLBACK_TTL = 300.0  # 5 min — same as adapter._news cache.
_cache = TTLCache(default_ttl=_FALLBACK_TTL)


def _finnhub_symbol(symbol: str, market: Market) -> str:
    """Reformat to the convention Finnhub expects:
       US -> bare uppercase ticker (e.g. AAPL)
       HK -> 4-digit code + .HK (e.g. 0700.HK)  (we normalise to 5 digits internally).
    """
    if market == "HK":
        base = symbol.upper().replace(".HK", "")
        # Finnhub uses 4-digit codes; trim leading zeros down to 4 chars.
        base = base.lstrip("0")
        if len(base) < 4:
            base = base.zfill(4)
        return f"{base}.HK"
    return symbol.upper()


async def _finnhub_company_news(symbol: str, key: str, limit: int) -> list[dict]:
    today = date.today()
    since = today - timedelta(days=14)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://finnhub.io/api/v1/company-news",
                params={
                    "symbol": symbol,
                    "from": since.isoformat(),
                    "to": today.isoformat(),
                    "token": key,
                },
            )
    except httpx.RequestError as e:
        logger.warning(f"finnhub news request failed for {symbol}: {e}")
        return []

    if r.status_code != 200:
        logger.warning(f"finnhub news {symbol}: HTTP {r.status_code}")
        return []
    try:
        items = r.json() or []
    except Exception:
        return []

    out: list[dict] = []
    for it in items[:limit]:
        out.append({
            "title": it.get("headline", ""),
            "publisher": it.get("source"),
            "url": it.get("url"),
            "published": it.get("datetime"),
            "summary": (it.get("summary") or "")[:500],
        })
    return out


async def aggregate_news(symbol: str, market: Market, limit: int = 10) -> list[dict]:
    """Pull from primary adapter; fall back to Finnhub for US/HK if empty.

    Cache layering:
    - adapter.news() is already TTL-cached inside the base class.
    - The Finnhub fallback is cached separately here (so we don't burn
      requests every time the primary keeps returning empty within TTL).
    """
    adapter = get_adapter(market)
    sym = adapter.normalize(symbol)

    primary = await adapter.news(sym, limit=limit)
    if primary:
        return primary
    if market == "CN":
        return primary  # akshare is the canonical source for A-shares

    s = get_settings()
    key = secrets.effective("finnhub", s.finnhub_api_key)
    if not key:
        return primary

    fb_symbol = _finnhub_symbol(sym, market)
    return await _cache.get_or_set(
        f"finnhub-news:{fb_symbol}:{limit}",
        lambda: _finnhub_company_news(fb_symbol, key, limit),
        ttl=_FALLBACK_TTL,
    )
