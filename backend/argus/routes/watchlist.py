"""Watchlist + alerts CRUD."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select


AlertMetric = Literal["price", "change_pct", "rsi_14"]
AlertOp = Literal[">", ">=", "<", "<=", "=="]

from ..analysis.indicators import compute_indicators
from ..markets import detect_market, get_adapter
from ..storage import AlertRule, WatchlistItem, get_session

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddItem(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    note: str = Field(default="", max_length=500)


class AddAlert(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    metric: AlertMetric
    op: AlertOp
    threshold: float
    note: str = Field(default="", max_length=500)


@router.get("")
async def list_items(session: Session = Depends(get_session)):
    items = list(session.exec(select(WatchlistItem)).all())
    enriched = []
    for it in items:
        try:
            adapter = get_adapter(it.market)
            quote = await adapter.quote(it.symbol)
            enriched.append({**it.model_dump(), "quote": quote.model_dump()})
        except Exception:
            enriched.append({**it.model_dump(), "quote": None})
    return {"items": enriched}


@router.post("")
async def add_item(body: AddItem, session: Session = Depends(get_session)):
    market = detect_market(body.symbol)
    adapter = get_adapter(market)
    sym = adapter.normalize(body.symbol)
    existing = session.exec(select(WatchlistItem).where(WatchlistItem.symbol == sym)).first()
    if existing:
        return {"item": existing.model_dump(), "created": False}
    try:
        quote = await adapter.quote(body.symbol)
        name = quote.name
    except Exception:
        name = ""
    item = WatchlistItem(symbol=sym, market=market, name=name, note=body.note)
    session.add(item)
    session.commit()
    session.refresh(item)
    return {"item": item.model_dump(), "created": True}


@router.delete("/{item_id}")
def delete_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(WatchlistItem, item_id)
    if not item:
        raise HTTPException(404, "not found")
    session.delete(item)
    session.commit()
    return {"ok": True}


@router.get("/alerts")
def list_alerts(session: Session = Depends(get_session)):
    rules = list(session.exec(select(AlertRule)).all())
    return {"alerts": [r.model_dump() for r in rules]}


@router.post("/alerts")
def add_alert(body: AddAlert, session: Session = Depends(get_session)):
    market = detect_market(body.symbol)
    adapter = get_adapter(market)
    sym = adapter.normalize(body.symbol)
    rule = AlertRule(
        symbol=sym, market=market, metric=body.metric, op=body.op,
        threshold=body.threshold, note=body.note,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return {"alert": rule.model_dump()}


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int, session: Session = Depends(get_session)):
    rule = session.get(AlertRule, alert_id)
    if not rule:
        raise HTTPException(404, "not found")
    session.delete(rule)
    session.commit()
    return {"ok": True}


def _cmp(value: float, op: str, threshold: float) -> bool:
    return {
        ">": value > threshold,
        "<": value < threshold,
        ">=": value >= threshold,
        "<=": value <= threshold,
        "==": value == threshold,
    }.get(op, False)


@router.post("/alerts/evaluate")
async def evaluate_alerts(session: Session = Depends(get_session)):
    """One-shot evaluation pass — returns triggered alerts. UI can poll this."""
    rules = list(session.exec(select(AlertRule).where(AlertRule.active == True)).all())  # noqa: E712
    triggered: list[dict] = []
    for rule in rules:
        try:
            adapter = get_adapter(rule.market)
            quote = await adapter.quote(rule.symbol)
            value: float | None = None
            if rule.metric == "price":
                value = quote.price
            elif rule.metric == "change_pct":
                value = quote.change_pct
            elif rule.metric == "rsi_14":
                hist = await adapter.history(rule.symbol, interval="1d")
                ind = compute_indicators(hist[-260:])
                value = (ind.get("latest") or {}).get("rsi_14")
            if value is None:
                continue
            if _cmp(value, rule.op, rule.threshold):
                rule.last_triggered = datetime.utcnow()
                session.add(rule)
                triggered.append({
                    "rule": rule.model_dump(),
                    "value": value,
                    "quote": quote.model_dump(),
                })
        except Exception:
            continue
    session.commit()
    return {"triggered": triggered, "evaluated": len(rules)}
