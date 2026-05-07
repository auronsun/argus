"""Smart-money positioning signals — the data the 6th analyst (Flow Analyst) reads.

Gathers per-market signals that mainstream retail tools rarely surface:

* **A-share (CN)** — 龙虎榜异常席位 / 北向资金净流入 / 融资融券余额变化  (akshare, free)
* **US**          — Form 4 insider transactions (Finnhub) + short interest (yfinance basic)
* **HK**          — short selling % (basic — best-effort via akshare; minimal coverage in v1)

Every fetch is wrapped in try/except + cached. Missing signals come back as
empty / None — the LLM is instructed to acknowledge gaps rather than
hallucinate numbers.
"""
from __future__ import annotations

import asyncio
import re
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from pydantic import BaseModel, Field

from ..config import get_settings
from ..markets.base import Market
from ..storage import secrets
from ..utils import logger
from ..utils.cache import TTLCache


_FLOW_TTL = 1800.0  # 30 minutes — flow data is daily-ish, no need for tighter
_cache = TTLCache(default_ttl=_FLOW_TTL)


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------

class InsiderTxn(BaseModel):
    date: str = ""
    name: str = ""
    role: str = ""
    type: str = ""        # "BUY" | "SELL" | other
    shares: float | None = None
    value: float | None = None  # USD


class LHBEntry(BaseModel):
    """One 龙虎榜 (Dragon-Tiger List) appearance for a CN ticker."""
    date: str = ""
    reason: str = ""
    top_buyers: list[str] = Field(default_factory=list)
    top_sellers: list[str] = Field(default_factory=list)
    net_buy_amount: float | None = None  # CNY


class FlowSignals(BaseModel):
    market: Market
    symbol: str

    # ---- US ----
    insider_transactions: list[InsiderTxn] = Field(default_factory=list)
    insider_net_buy_count: int = 0     # buys - sells in window
    insider_net_buy_value: float | None = None  # USD net
    short_pct_float: float | None = None
    short_ratio_dtc: float | None = None  # days-to-cover

    # ---- CN ----
    lhb_recent: list[LHBEntry] = Field(default_factory=list)
    northbound_5d_net_cny: float | None = None
    margin_balance_5d_change_pct: float | None = None

    # ---- HK ----
    hk_short_selling_pct: float | None = None

    # ---- universal ----
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

async def aggregate_flow(symbol: str, market: Market) -> FlowSignals:
    """Resolve all flow signals for a ticker. Cached per (market, symbol).

    Always returns a FlowSignals — fields just stay empty if the underlying
    fetch fails or the data source isn't available. The agent is told this.
    """
    key = f"flow:{market}:{symbol}"
    try:
        return await _cache.get_or_set(
            key, lambda: _fetch(symbol, market), ttl=_FLOW_TTL,
        )
    except Exception as e:
        logger.warning(f"flow.aggregate_flow {market}:{symbol} failed: {e}")
        return FlowSignals(market=market, symbol=symbol,
                           notes=[f"Flow signals unavailable: {e}"])


async def _fetch(symbol: str, market: Market) -> FlowSignals:
    if market == "US":
        return await _fetch_us(symbol)
    if market == "CN":
        return await _fetch_cn(symbol)
    if market == "HK":
        return await _fetch_hk(symbol)
    return FlowSignals(market=market, symbol=symbol)


# ===========================================================================
# US — Finnhub insiders + yfinance short
# ===========================================================================

async def _fetch_us(symbol: str) -> FlowSignals:
    out = FlowSignals(market="US", symbol=symbol)

    # Insider transactions (Finnhub) — needs a key; degrades silently otherwise.
    s = get_settings()
    fnh = secrets.effective("finnhub", s.finnhub_api_key)
    if fnh:
        try:
            since = (date.today() - timedelta(days=90)).isoformat()
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://finnhub.io/api/v1/stock/insider-transactions",
                    params={"symbol": symbol, "from": since, "token": fnh},
                )
            if r.status_code == 200:
                payload = r.json()
                rows = payload.get("data") or []
                buys = sells = 0
                value_buy = value_sell = 0.0
                for row in rows[:60]:
                    change = float(row.get("change") or 0)
                    price = float(row.get("transactionPrice") or 0)
                    txn_value = abs(change) * price
                    txn_type = "BUY" if change > 0 else "SELL" if change < 0 else "OTHER"
                    if txn_type == "BUY":
                        buys += 1
                        value_buy += txn_value
                    elif txn_type == "SELL":
                        sells += 1
                        value_sell += txn_value
                    out.insider_transactions.append(InsiderTxn(
                        date=str(row.get("transactionDate") or ""),
                        name=str(row.get("name") or ""),
                        role="",  # Finnhub doesn't always populate; fine to leave empty
                        type=txn_type,
                        shares=abs(change) or None,
                        value=txn_value or None,
                    ))
                out.insider_net_buy_count = buys - sells
                out.insider_net_buy_value = value_buy - value_sell
            else:
                out.notes.append(f"insider fetch HTTP {r.status_code}")
        except Exception as e:
            logger.warning(f"finnhub insider fetch failed for {symbol}: {e}")
            out.notes.append("insider data unavailable (Finnhub)")
    else:
        out.notes.append("insider data unavailable (no Finnhub key)")

    # Short interest via yfinance (basic — sharesShort / shortRatio in info)
    try:
        import yfinance as yf
        info = await asyncio.to_thread(lambda: yf.Ticker(symbol).info or {})
        short_shares = info.get("sharesShort")
        float_shares = info.get("floatShares") or info.get("sharesOutstanding")
        if short_shares and float_shares:
            out.short_pct_float = float(short_shares) / float(float_shares) * 100
        out.short_ratio_dtc = float(info.get("shortRatio") or 0) or None
    except Exception as e:
        logger.warning(f"yfinance short fetch failed for {symbol}: {e}")
        out.notes.append("short interest unavailable")

    return out


# ===========================================================================
# CN — akshare 龙虎榜 + 北向 + 融资融券
# ===========================================================================

def _cn_code(symbol: str) -> str:
    """'600519.SH' → '600519' for akshare."""
    return re.sub(r"\.(SH|SS|SZ|BJ)$", "", symbol.strip().upper())


async def _fetch_cn(symbol: str) -> FlowSignals:
    out = FlowSignals(market="CN", symbol=symbol)
    code = _cn_code(symbol)

    # Run the three fetches in parallel; each tolerates failure.
    results = await asyncio.gather(
        asyncio.to_thread(_cn_lhb_recent, code),
        asyncio.to_thread(_cn_northbound_5d, code),
        asyncio.to_thread(_cn_margin_5d_change, code),
        return_exceptions=True,
    )

    if isinstance(results[0], list):
        out.lhb_recent = results[0]  # type: ignore[assignment]
    elif isinstance(results[0], Exception):
        out.notes.append(f"龙虎榜 unavailable: {results[0]}")

    if isinstance(results[1], (int, float)):
        out.northbound_5d_net_cny = float(results[1])  # type: ignore[arg-type]
    elif isinstance(results[1], Exception):
        out.notes.append(f"北向资金 unavailable: {results[1]}")

    if isinstance(results[2], (int, float)):
        out.margin_balance_5d_change_pct = float(results[2])  # type: ignore[arg-type]
    elif isinstance(results[2], Exception):
        out.notes.append(f"融资融券 unavailable: {results[2]}")

    return out


def _cn_lhb_recent(code: str) -> list[LHBEntry]:
    """Recent ~30-day 龙虎榜 entries for a stock.

    Uses the broad-market endpoint (`stock_lhb_detail_em(start, end)`) and
    filters by the 代码 column. The per-stock function `stock_lhb_stock_detail_em`
    has a known akshare bug that raises `'NoneType' is not subscriptable` when
    the stock has no recent appearances, so we deliberately avoid it.
    """
    import akshare as ak

    end = date.today()
    start = end - timedelta(days=30)
    try:
        df = ak.stock_lhb_detail_em(
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )
    except Exception as e:
        logger.debug(f"lhb broad fetch failed: {e}")
        return []
    if df is None or df.empty:
        return []

    code_col = next((c for c in df.columns if str(c) in ("代码", "股票代码")), None)
    if code_col is None:
        return []
    df = df[df[code_col].astype(str).str.zfill(6) == code]
    if df.empty:
        return []

    out: list[LHBEntry] = []
    for _, row in df.head(10).iterrows():
        date_v = row.get("上榜日") or row.get("交易日") or ""
        reason = row.get("上榜原因") or row.get("解读") or ""
        net = row.get("龙虎榜净买额") or row.get("净买入额") or row.get("龙虎榜净买额") or None
        try:
            net = float(net) if net is not None else None
        except (TypeError, ValueError):
            net = None
        out.append(LHBEntry(
            date=str(date_v)[:10],
            reason=str(reason)[:100],
            net_buy_amount=net,
        ))
    return out


def _cn_northbound_5d(code: str) -> float | None:
    """5-day net Stock Connect (北向资金) flow for an A-share, in CNY.
    Positive = net buy.
    """
    import akshare as ak

    fn = getattr(ak, "stock_hsgt_individual_em", None)
    if fn is None:
        return None
    try:
        df = fn(symbol=code)  # akshare arg name is `symbol`, not `stock`
    except Exception as e:
        logger.debug(f"northbound fetch failed for {code}: {e}")
        return None
    if df is None or df.empty:
        return None

    # akshare's stock_hsgt_individual_em uses '今日增持资金' (CNY net add) as
    # the per-day flow column. Prior names tried as fallback for older versions.
    candidates = [
        "今日增持资金",
        "持股市值变化-1日", "持股市值变化-1日(元)",
        "净买额", "北向净买额", "净流入额",
    ]
    col = next((c for c in candidates if c in df.columns), None)
    if col is None:
        col = next(
            (c for c in df.columns if "增持资金" in str(c) or "净买" in str(c) or "净流入" in str(c)),
            None,
        )
    if col is None:
        return None

    df = df.tail(5)
    try:
        return float(df[col].astype(float).sum())
    except Exception:
        return None


def _cn_margin_5d_change(code: str) -> float | None:
    """v1: not implemented — akshare's per-stock margin endpoints are unstable
    and the broad daily endpoint is too large to fetch reliably from clients.
    Return None; the agent will note that margin data is unavailable."""
    return None


# ===========================================================================
# HK — best-effort short selling %; minimal in v1
# ===========================================================================

async def _fetch_hk(symbol: str) -> FlowSignals:
    out = FlowSignals(market="HK", symbol=symbol)
    out.notes.append("HK flow signals not yet wired (planned: HKEX short selling, CCASS)")
    return out
