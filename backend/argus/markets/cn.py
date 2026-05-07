"""A-share (Shanghai/Shenzhen) adapter, powered by akshare."""
from __future__ import annotations

import asyncio
import re
from datetime import date, datetime, timedelta
from typing import Optional

import akshare as ak
import pandas as pd

from ..utils import logger
from .base import (
    Candle,
    Fundamentals,
    Interval,
    MarketAdapter,
    Quote,
    SymbolSearchResult,
)


_PERIOD_MAP: dict[Interval, str] = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "1d": "daily",
    "1wk": "weekly",
    "1mo": "monthly",
}


def _to_thread(fn, *args, **kwargs):
    return asyncio.to_thread(fn, *args, **kwargs)


def _strip_suffix(symbol: str) -> str:
    """'600519.SH' / '600519.SS' -> '600519'."""
    return re.sub(r"\.(SH|SS|SZ|BJ)$", "", symbol.strip().upper())


def _add_suffix(code: str) -> str:
    code = code.lstrip("0") or "0"
    raw = code if code.isdigit() else _strip_suffix(code)
    raw = raw.zfill(6)
    if raw.startswith(("60", "68", "9")):
        return f"{raw}.SH"
    if raw.startswith(("00", "30", "20")):
        return f"{raw}.SZ"
    if raw.startswith(("8", "4")):
        return f"{raw}.BJ"
    return f"{raw}.SH"


class CNAdapter(MarketAdapter):
    market = "CN"

    def normalize(self, symbol: str) -> str:
        return _add_suffix(symbol)

    async def _quote(self, symbol: str) -> Quote:
        code = _strip_suffix(symbol)
        try:
            df = await _to_thread(lambda: ak.stock_bid_ask_em(symbol=code))
        except Exception as e:
            logger.warning(f"akshare bid/ask failed for {code}: {e}; falling back to spot")
            df = pd.DataFrame()
        snap = {}
        if not df.empty:
            snap = dict(zip(df["item"], df["value"]))

        # Fall back to the spot board for name + missing fields
        try:
            spot = await _to_thread(lambda: ak.stock_zh_a_spot_em())
            row = spot[spot["代码"] == code]
            if not row.empty:
                r = row.iloc[0]
                price = float(snap.get("最新", r["最新价"]))
                prev = float(snap.get("昨收", r.get("昨收", 0)) or 0)
                return Quote(
                    symbol=self.normalize(code),
                    market="CN",
                    name=str(r["名称"]),
                    price=price,
                    change=float(r["涨跌额"]),
                    change_pct=float(r["涨跌幅"]),
                    open=float(r["今开"]),
                    high=float(r["最高"]),
                    low=float(r["最低"]),
                    prev_close=prev or None,
                    volume=float(r["成交量"]),
                    market_cap=float(r.get("总市值", 0) or 0) or None,
                    currency="CNY",
                )
        except Exception as e:
            logger.warning(f"akshare spot board failed: {e}")

        # Last resort
        price = float(snap.get("最新", 0) or 0)
        return Quote(symbol=self.normalize(code), market="CN", price=price, currency="CNY")

    async def _history(
        self,
        symbol: str,
        interval: Interval = "1d",
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> list[Candle]:
        code = _strip_suffix(symbol)
        period = _PERIOD_MAP.get(interval, "daily")
        end = end or date.today()
        start = start or (end - timedelta(days=730))

        if interval in ("1d", "1wk", "1mo"):
            df = await _to_thread(
                lambda: ak.stock_zh_a_hist(
                    symbol=code,
                    period=period,
                    start_date=start.strftime("%Y%m%d"),
                    end_date=end.strftime("%Y%m%d"),
                    adjust="qfq",
                )
            )
            time_col = "日期"
        else:
            df = await _to_thread(
                lambda: ak.stock_zh_a_hist_min_em(
                    symbol=code,
                    period=period,
                    start_date=start.strftime("%Y-%m-%d 09:30:00"),
                    end_date=end.strftime("%Y-%m-%d 15:00:00"),
                    adjust="qfq",
                )
            )
            time_col = "时间"

        if df is None or df.empty:
            return []
        out: list[Candle] = []
        for _, row in df.iterrows():
            t = row[time_col]
            if isinstance(t, str):
                t = pd.to_datetime(t).to_pydatetime()
            elif hasattr(t, "to_pydatetime"):
                t = t.to_pydatetime()
            out.append(
                Candle(
                    time=t,
                    open=float(row["开盘"]),
                    high=float(row["最高"]),
                    low=float(row["最低"]),
                    close=float(row["收盘"]),
                    volume=float(row.get("成交量", 0) or 0),
                )
            )
        return out

    async def _fundamentals(self, symbol: str) -> Fundamentals:
        code = _strip_suffix(symbol)
        try:
            df = await _to_thread(lambda: ak.stock_individual_info_em(symbol=code))
            info = dict(zip(df["item"], df["value"])) if not df.empty else {}
        except Exception as e:
            logger.warning(f"akshare individual_info failed: {e}")
            info = {}
        return Fundamentals(
            symbol=self.normalize(code),
            market="CN",
            name=str(info.get("股票简称", "")),
            sector=str(info.get("行业") or "") or None,
            industry=str(info.get("行业") or "") or None,
            market_cap=float(info.get("总市值") or 0) or None,
            currency="CNY",
            pe_ratio=None,
            pb_ratio=None,
            summary=None,
        )

    async def _search(self, query: str, limit: int = 10) -> list[SymbolSearchResult]:
        """Resolve search queries WITHOUT scanning the full A-share board.

        akshare's `stock_zh_a_spot_em()` returns 5,000+ rows and is slow
        + flaky on every keystroke. We instead:
          * pure-digit queries → construct the canonical symbol directly
            via `_add_suffix` (handles SH/SZ/STAR/ChiNext/BJ).
          * text queries (Chinese / English) → match a curated list of
            widely-traded A-shares in `popular.py`.
        """
        from .popular import search_cn

        q = query.strip()
        if not q:
            return []

        def _exchange(code: str) -> str:
            return "SSE" if code.startswith(("60", "68", "9")) else (
                "BJSE" if code.startswith(("8", "4")) else "SZSE"
            )

        if q.isdigit():
            # A-share codes are exactly 6 digits — any other length can't
            # be a CN ticker. We still allow shorter prefixes so the
            # curated list can prefix-match while typing.
            hits = search_cn(q, limit=limit)
            results: list[SymbolSearchResult] = []
            seen: set[str] = set()
            for code, display in hits:
                sym = _add_suffix(code)
                if sym in seen:
                    continue
                seen.add(sym)
                results.append(SymbolSearchResult(
                    symbol=sym, name=display, market="CN", exchange=_exchange(code),
                ))
            # Synthesise the direct ticker only when length is exactly 6 —
            # avoids phantom CN matches when the user is typing an HK code.
            if len(q) == 6:
                primary = _add_suffix(q)
                if primary not in seen:
                    results.insert(0, SymbolSearchResult(
                        symbol=primary, name="", market="CN",
                        exchange=_exchange(q),
                    ))
            return results[:limit]

        # Text query — search the curated list.
        return [
            SymbolSearchResult(
                symbol=_add_suffix(code),
                name=display,
                market="CN",
                exchange=_exchange(code),
            )
            for code, display in search_cn(q, limit=limit)
        ]

    async def _news(self, symbol: str, limit: int = 10) -> list[dict]:
        code = _strip_suffix(symbol)
        try:
            df = await _to_thread(lambda: ak.stock_news_em(symbol=code))
        except Exception as e:
            logger.warning(f"akshare news failed for {code}: {e}")
            return []
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.head(limit).iterrows():
            out.append(
                {
                    "title": str(row.get("新闻标题", "")),
                    "publisher": str(row.get("文章来源", "")),
                    "url": str(row.get("新闻链接", "")),
                    "published": str(row.get("发布时间", "")),
                    "summary": str(row.get("新闻内容", ""))[:500],
                }
            )
        return out
