"""Hong Kong (HKEX) adapter — primarily yfinance with akshare for fundamentals."""
from __future__ import annotations

import asyncio
import re
from datetime import date, datetime, timedelta
from typing import Optional

import akshare as ak
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
from .us import _INTERVAL_MAP


def _to_thread(fn, *args, **kwargs):
    return asyncio.to_thread(fn, *args, **kwargs)


def _hk_strip(symbol: str) -> str:
    s = symbol.strip().upper()
    s = re.sub(r"\.HK$", "", s)
    return s.lstrip("0").zfill(5)


def _hk_yf(code: str) -> str:
    return f"{code.lstrip('0').zfill(4)}.HK"


class HKAdapter(MarketAdapter):
    market = "HK"

    def normalize(self, symbol: str) -> str:
        return f"{_hk_strip(symbol)}.HK"

    async def _quote(self, symbol: str) -> Quote:
        code = _hk_strip(symbol)
        yf_sym = _hk_yf(code)
        ticker = yf.Ticker(yf_sym)
        info = await _to_thread(lambda: ticker.fast_info)
        full = await _to_thread(lambda: getattr(ticker, "info", {}) or {})
        price = float(info.get("last_price") or full.get("currentPrice") or 0.0)
        prev = float(info.get("previous_close") or full.get("previousClose") or 0.0)
        change = price - prev if prev else 0.0
        change_pct = (change / prev * 100) if prev else 0.0
        return Quote(
            symbol=self.normalize(code),
            market="HK",
            name=full.get("shortName") or full.get("longName") or yf_sym,
            price=price,
            change=change,
            change_pct=change_pct,
            open=float(info.get("open") or 0.0) or None,
            high=float(info.get("day_high") or 0.0) or None,
            low=float(info.get("day_low") or 0.0) or None,
            prev_close=prev or None,
            volume=float(info.get("last_volume") or 0.0) or None,
            market_cap=full.get("marketCap"),
            currency="HKD",
        )

    async def _history(
        self,
        symbol: str,
        interval: Interval = "1d",
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> list[Candle]:
        code = _hk_strip(symbol)
        yf_sym = _hk_yf(code)
        yf_int = _INTERVAL_MAP.get(interval, "1d")
        period_kwargs = {}
        if start is None and end is None:
            period_kwargs["period"] = "2y" if interval in ("1d", "1wk", "1mo") else "60d"
        df = await _to_thread(
            lambda: yf.Ticker(yf_sym).history(
                interval=yf_int, start=start, end=end, auto_adjust=False, **period_kwargs
            )
        )
        if df.empty:
            return []
        out = []
        for ts, row in df.iterrows():
            t = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else datetime.fromisoformat(str(ts))
            out.append(
                Candle(
                    time=t,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row.get("Volume", 0) or 0),
                )
            )
        return out

    async def _fundamentals(self, symbol: str) -> Fundamentals:
        code = _hk_strip(symbol)
        yf_sym = _hk_yf(code)
        info = await _to_thread(lambda: yf.Ticker(yf_sym).info or {})
        return Fundamentals(
            symbol=self.normalize(code),
            market="HK",
            name=info.get("shortName") or info.get("longName") or yf_sym,
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=info.get("marketCap"),
            currency="HKD",
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
        # akshare ships a HK ticker board; use it for richer Chinese names
        try:
            df = await _to_thread(lambda: ak.stock_hk_spot_em())
        except Exception as e:
            logger.warning(f"akshare HK board failed: {e}")
            return []
        q = query.strip()
        if not q:
            return []
        if q.isdigit():
            mask = df["代码"].astype(str).str.lstrip("0").str.startswith(q.lstrip("0") or "0")
        else:
            mask = df["名称"].astype(str).str.contains(q, regex=False, case=False)
        hits = df[mask].head(limit)
        return [
            SymbolSearchResult(
                symbol=self.normalize(str(row["代码"])),
                name=str(row["名称"]),
                market="HK",
                exchange="HKEX",
            )
            for _, row in hits.iterrows()
        ]
