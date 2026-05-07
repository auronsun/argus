"""US market adapter — yfinance baseline, with optional premium provider hooks."""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Optional

import yfinance as yf

from ..utils import logger
from .base import (
    Candle,
    Fundamentals,
    Interval,
    MarketAdapter,
    Quote,
    SymbolSearchResult,
)


_INTERVAL_MAP: dict[Interval, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "60m",
    "1d": "1d",
    "1wk": "1wk",
    "1mo": "1mo",
}


def _to_thread(fn, *args, **kwargs):
    return asyncio.to_thread(fn, *args, **kwargs)


class USAdapter(MarketAdapter):
    market = "US"

    def normalize(self, symbol: str) -> str:
        return symbol.strip().upper()

    async def _quote(self, symbol: str) -> Quote:
        sym = symbol  # already normalised by base
        ticker = yf.Ticker(sym)
        info = await _to_thread(lambda: ticker.fast_info)
        full = await _to_thread(lambda: getattr(ticker, "info", {}) or {})
        price = float(info.get("last_price") or info.get("lastPrice") or full.get("currentPrice") or 0.0)
        prev = float(info.get("previous_close") or info.get("previousClose") or full.get("previousClose") or 0.0)
        change = price - prev if prev else 0.0
        change_pct = (change / prev * 100) if prev else 0.0
        return Quote(
            symbol=sym,
            market="US",
            # Prefer longName — more descriptive for the LLM, and yfinance
            # sometimes gives an obscure ALL-CAPS slug as shortName.
            name=full.get("longName") or full.get("shortName") or sym,
            price=price,
            change=change,
            change_pct=change_pct,
            open=float(info.get("open") or full.get("open") or 0.0) or None,
            high=float(info.get("day_high") or full.get("dayHigh") or 0.0) or None,
            low=float(info.get("day_low") or full.get("dayLow") or 0.0) or None,
            prev_close=prev or None,
            volume=float(info.get("last_volume") or full.get("volume") or 0.0) or None,
            market_cap=float(full.get("marketCap") or 0.0) or None,
            currency=str(info.get("currency") or full.get("currency") or "USD"),
        )

    async def _history(
        self,
        symbol: str,
        interval: Interval = "1d",
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> list[Candle]:
        sym = symbol
        yf_int = _INTERVAL_MAP.get(interval, "1d")
        period_kwargs = {}
        if start is None and end is None:
            period_kwargs["period"] = "2y" if interval in ("1d", "1wk", "1mo") else "60d"
        df = await _to_thread(
            lambda: yf.Ticker(sym).history(
                interval=yf_int,
                start=start,
                end=end,
                auto_adjust=False,
                **period_kwargs,
            )
        )
        if df.empty:
            return []
        candles: list[Candle] = []
        for ts, row in df.iterrows():
            candles.append(
                Candle(
                    time=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else datetime.fromisoformat(str(ts)),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row.get("Volume", 0) or 0),
                )
            )
        return candles

    async def _fundamentals(self, symbol: str) -> Fundamentals:
        sym = symbol
        info = await _to_thread(lambda: yf.Ticker(sym).info or {})
        return Fundamentals(
            symbol=sym,
            market="US",
            name=info.get("longName") or info.get("shortName") or sym,
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=info.get("marketCap"),
            currency=info.get("currency", "USD"),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            pb_ratio=info.get("priceToBook"),
            ps_ratio=info.get("priceToSalesTrailing12Months"),
            dividend_yield=info.get("dividendYield"),
            eps=info.get("trailingEps"),
            revenue_ttm=info.get("totalRevenue"),
            profit_margin=info.get("profitMargins"),
            beta=info.get("beta"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
            summary=info.get("longBusinessSummary"),
        )

    async def _search(self, query: str, limit: int = 10) -> list[SymbolSearchResult]:
        try:
            res = await _to_thread(lambda: yf.Search(query, max_results=limit))
            quotes = getattr(res, "quotes", []) or []
        except Exception as e:
            logger.warning(f"yfinance search failed: {e}")
            return []
        out: list[SymbolSearchResult] = []
        for q in quotes:
            if q.get("quoteType") not in ("EQUITY", "ETF", None):
                continue
            sym = q.get("symbol", "")
            if "." in sym:  # filter out non-US listings here
                continue
            out.append(
                SymbolSearchResult(
                    symbol=sym,
                    name=q.get("shortname") or q.get("longname") or sym,
                    market="US",
                    exchange=q.get("exchange"),
                )
            )
            if len(out) >= limit:
                break
        return out

    async def _news(self, symbol: str, limit: int = 10) -> list[dict]:
        sym = symbol
        try:
            items = await _to_thread(lambda: yf.Ticker(sym).news or [])
        except Exception as e:
            logger.warning(f"yfinance news failed for {sym}: {e}")
            return []
        out = []
        for it in items[:limit]:
            content = it.get("content") or it
            out.append(
                {
                    "title": content.get("title", ""),
                    "publisher": (content.get("provider") or {}).get("displayName") if isinstance(content.get("provider"), dict) else content.get("publisher"),
                    "url": (content.get("canonicalUrl") or {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else content.get("link"),
                    "published": content.get("pubDate") or content.get("providerPublishTime"),
                    "summary": content.get("summary", ""),
                }
            )
        return out
