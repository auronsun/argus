"""Multi-agent investment-committee endpoint — Server-Sent Events stream."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..agents import InvestmentCommittee
from ..markets.base import Market

router = APIRouter(prefix="/api/committee", tags=["committee"])


AnalystRole = Literal[
    "technical", "fundamental", "sentiment", "macro", "risk", "flow", "cio",
]


class RetryRequest(BaseModel):
    role: AnalystRole
    lang: Literal["en", "zh"] = "en"
    market: Optional[Market] = None
    # Outputs already produced by the OTHER analysts on the previous run,
    # so the CIO can re-synthesise without re-running everyone. Keys must
    # be analyst role names; the role being retried may be omitted.
    existing_outputs: dict[str, str] = Field(default_factory=dict)


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


@router.post("/retry/{symbol:path}")
async def retry(symbol: str, body: RetryRequest):
    """Re-run a single analyst (or just the CIO) with the outputs the
    client still has from the prior run. SSE shape matches the main
    `/stream` endpoint."""
    committee = InvestmentCommittee(lang=body.lang)

    async def event_source():
        try:
            async for ev in committee.stream_retry(
                symbol,
                role=body.role,
                existing_outputs=body.existing_outputs,
                market=body.market,
            ):
                yield f"data: {ev.to_json()}\n\n"
        except Exception as e:
            import json as _json
            yield f"data: {_json.dumps({'type': 'error', 'text': str(e)})}\n\n"
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
