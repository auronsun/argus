"""Market data endpoints — quotes, history, search, news."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..analysis import aggregate_news
from ..markets import detect_market, get_adapter, search_symbols
from ..markets.base import Interval, Market

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1, max_length=64),
    limit: int = Query(10, ge=1, le=50),
):
    results = await search_symbols(q, limit=limit)
    return {"query": q, "results": [r.model_dump() for r in results]}


@router.get("/quote/{symbol:path}")
async def quote(symbol: str, market: Optional[Market] = None):
    adapter = get_adapter(market or symbol)
    try:
        q = await adapter.quote(symbol)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"quote failed: {e}")
    return q.model_dump()


@router.get("/history/{symbol:path}")
async def history(
    symbol: str,
    market: Optional[Market] = None,
    interval: Interval = "1d",
    start: Optional[date] = None,
    end: Optional[date] = None,
):
    adapter = get_adapter(market or symbol)
    try:
        candles = await adapter.history(symbol, interval=interval, start=start, end=end)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"history failed: {e}")
    return {"symbol": adapter.normalize(symbol), "interval": interval, "candles": [c.model_dump() for c in candles]}


@router.get("/news/{symbol:path}")
async def news(
    symbol: str,
    market: Optional[Market] = None,
    limit: int = Query(10, ge=1, le=50),
):
    resolved_market: Market = market or detect_market(symbol)
    adapter = get_adapter(resolved_market)
    try:
        items = await aggregate_news(symbol, resolved_market, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"news failed: {e}")
    return {"symbol": adapter.normalize(symbol), "items": items}


@router.get("/detect")
def detect(symbol: str):
    return {"symbol": symbol, "market": detect_market(symbol)}
