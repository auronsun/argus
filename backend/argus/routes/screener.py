"""Cross-market screener endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..analysis import ScreenerCriteria, run_screener

router = APIRouter(prefix="/api/screener", tags=["screener"])


PRESETS: dict[str, ScreenerCriteria] = {
    "momentum": ScreenerCriteria(min_change_pct=2.0, rsi_above=55, require_golden_cross=True, limit=30),
    "oversold": ScreenerCriteria(rsi_below=30, limit=30),
    # 'value' currently mirrors 'all'; extend once richer fundamentals are wired.
    "value":    ScreenerCriteria(limit=30),
    "all":      ScreenerCriteria(limit=60),
}


@router.post("/run")
async def run(criteria: ScreenerCriteria):
    rows = await run_screener(criteria)
    return {"count": len(rows), "rows": rows}


@router.get("/presets")
def list_presets():
    return {"presets": list(PRESETS.keys())}


@router.get("/preset/{name}")
async def preset(name: str):
    if name not in PRESETS:
        raise HTTPException(status_code=404, detail=f"unknown preset '{name}'")
    rows = await run_screener(PRESETS[name])
    return {"preset": name, "count": len(rows), "rows": rows}
