"""Abstract market-data interface and core domain models."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from ..utils import TTLCache


Market = Literal["US", "CN", "HK"]
Interval = Literal["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"]


class Quote(BaseModel):
    symbol: str
    market: Market
    name: str = ""
    price: float
    change: float = 0.0
    change_pct: float = 0.0
    open: float | None = None
    high: float | None = None
    low: float | None = None
    prev_close: float | None = None
    volume: float | None = None
    market_cap: float | None = None
    currency: str = "USD"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Candle(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class Fundamentals(BaseModel):
    symbol: str
    market: Market
    name: str = ""
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    currency: str = "USD"
    pe_ratio: float | None = None
    forward_pe: float | None = None
    pb_ratio: float | None = None
    ps_ratio: float | None = None
    dividend_yield: float | None = None
    eps: float | None = None
    revenue_ttm: float | None = None
    profit_margin: float | None = None
    beta: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    summary: str | None = None


class SymbolSearchResult(BaseModel):
    symbol: str
    name: str
    market: Market
    exchange: str | None = None


class MarketAdapter(ABC):
    """One adapter per market. Implementations should be safe to call concurrently.

    Subclasses implement `_quote`, `_history`, `_fundamentals`, `_search`, `_news`
    (the actual upstream calls). The public `quote` / `history` / etc. methods are
    provided here and add a TTL cache on top so multiple panels can request the
    same symbol without amplifying load on yfinance / akshare.
    """

    market: Market

    # TTLs per kind of call — tuned for OSS friendliness; safe upper bound.
    QUOTE_TTL = 5.0
    HISTORY_TTL = 300.0
    FUNDAMENTALS_TTL = 1800.0
    SEARCH_TTL = 600.0
    NEWS_TTL = 300.0

    def __init__(self) -> None:
        self._cache = TTLCache(default_ttl=60.0)

    # ---- public, cached -----------------------------------------------------

    async def quote(self, symbol: str) -> "Quote":
        sym = self.normalize(symbol)
        return await self._cache.get_or_set(
            f"q:{self.market}:{sym}", lambda: self._quote(sym), ttl=self.QUOTE_TTL
        )

    async def history(
        self,
        symbol: str,
        interval: Interval = "1d",
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> list["Candle"]:
        sym = self.normalize(symbol)
        # Date-range queries skip the cache (callers usually want exact ranges).
        if start is not None or end is not None:
            return await self._history(sym, interval=interval, start=start, end=end)
        key = f"h:{self.market}:{sym}:{interval}"
        return await self._cache.get_or_set(
            key, lambda: self._history(sym, interval=interval), ttl=self.HISTORY_TTL
        )

    async def fundamentals(self, symbol: str) -> "Fundamentals":
        sym = self.normalize(symbol)
        return await self._cache.get_or_set(
            f"f:{self.market}:{sym}", lambda: self._fundamentals(sym), ttl=self.FUNDAMENTALS_TTL
        )

    async def search(self, query: str, limit: int = 10) -> list["SymbolSearchResult"]:
        q = (query or "").strip()
        if not q:
            return []
        return await self._cache.get_or_set(
            f"s:{self.market}:{q}:{limit}", lambda: self._search(q, limit=limit), ttl=self.SEARCH_TTL
        )

    async def news(self, symbol: str, limit: int = 10) -> list[dict]:
        sym = self.normalize(symbol)
        return await self._cache.get_or_set(
            f"n:{self.market}:{sym}:{limit}", lambda: self._news(sym, limit=limit), ttl=self.NEWS_TTL
        )

    # ---- subclass implementations ------------------------------------------

    @abstractmethod
    def normalize(self, symbol: str) -> str:
        """Return the canonical symbol for this market (e.g. '600519' -> '600519.SH')."""

    @abstractmethod
    async def _quote(self, symbol: str) -> "Quote": ...

    @abstractmethod
    async def _history(
        self,
        symbol: str,
        interval: Interval = "1d",
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> list["Candle"]: ...

    @abstractmethod
    async def _fundamentals(self, symbol: str) -> "Fundamentals": ...

    @abstractmethod
    async def _search(self, query: str, limit: int = 10) -> list["SymbolSearchResult"]: ...

    async def _news(self, symbol: str, limit: int = 10) -> list[dict]:
        """Default empty implementation; markets that have news should override."""
        return []
