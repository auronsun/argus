"""Indicator + fundamentals endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..analysis import compute_indicators, latest_signals
from ..markets import get_adapter
from ..markets.base import Interval, Market

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/indicators/{symbol:path}")
async def indicators(
    symbol: str,
    market: Optional[Market] = None,
    interval: Interval = "1d",
    lookback: int = Query(260, ge=60, le=2000),
):
    adapter = get_adapter(market or symbol)
    try:
        candles = await adapter.history(symbol, interval=interval)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"history failed: {e}")
    candles = candles[-max(lookback, 60):]
    ind = compute_indicators(candles)
    return {
        "symbol": adapter.normalize(symbol),
        "interval": interval,
        "indicators": ind,
        "signals": latest_signals(ind),
    }


@router.get("/fundamentals/{symbol:path}")
async def fundamentals(symbol: str, market: Optional[Market] = None):
    adapter = get_adapter(market or symbol)
    try:
        f = await adapter.fundamentals(symbol)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fundamentals failed: {e}")
    return f.model_dump()
