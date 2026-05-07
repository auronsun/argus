"""Multi-agent investment-committee endpoint — Server-Sent Events stream."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from ..agents import InvestmentCommittee
from ..markets.base import Market

router = APIRouter(prefix="/api/committee", tags=["committee"])


@router.get("/stream/{symbol:path}")
async def stream(
    symbol: str,
    market: Optional[Market] = None,
    lang: Literal["en", "zh"] = Query("en"),
):
    """SSE stream of committee events. Each event is `data: <json>\\n\\n`.

    `lang` controls the language analysts use in their commentary; CIO JSON
    keys remain in English regardless.
    """
    committee = InvestmentCommittee(lang=lang)

    async def event_source():
        try:
            async for ev in committee.stream(symbol, market=market):
                yield f"data: {ev.to_json()}\n\n"
        except Exception as e:
            err = {"type": "error", "text": str(e)}
            import json as _json
            yield f"data: {_json.dumps(err)}\n\n"
        yield "data: {\"type\":\"done\"}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
