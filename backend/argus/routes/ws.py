"""WebSocket endpoint for real-time quote streaming.

Polls underlying adapters at a tunable cadence and pushes deltas to the client.
A future iteration can swap this for vendor-native streaming (Finnhub, Longbridge,
etc.) without touching the frontend protocol.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..markets import detect_market, get_adapter
from ..utils import logger

router = APIRouter()


@router.websocket("/ws/quotes")
async def quotes_ws(ws: WebSocket):
    await ws.accept()
    subscriptions: dict[str, str] = {}  # canonical symbol -> market
    state = {"interval": 5.0}

    async def push_loop():
        while True:
            iv = state["interval"]
            if subscriptions:
                async def fetch(sym: str, mkt: str):
                    try:
                        q = await get_adapter(mkt).quote(sym)
                        return q.model_dump()
                    except Exception as e:
                        logger.debug(f"ws quote {sym} failed: {e}")
                        return None

                results = await asyncio.gather(*(fetch(s, m) for s, m in subscriptions.items()))
                for r in results:
                    if r:
                        await ws.send_text(json.dumps({"type": "quote", "data": r}))
            await asyncio.sleep(iv)

    push_task = asyncio.create_task(push_loop())
    try:
        while True:
            msg = await ws.receive_text()
            try:
                payload = json.loads(msg)
            except json.JSONDecodeError:
                continue
            action = payload.get("action")
            if action == "subscribe":
                for sym in payload.get("symbols", []):
                    market = payload.get("market") or detect_market(sym)
                    subscriptions[get_adapter(market).normalize(sym)] = market
                await ws.send_text(json.dumps({"type": "subscribed", "symbols": list(subscriptions.keys())}))
            elif action == "unsubscribe":
                for sym in payload.get("symbols", []):
                    market = detect_market(sym)
                    subscriptions.pop(get_adapter(market).normalize(sym), None)
            elif action == "set_interval":
                state["interval"] = max(1.0, float(payload.get("interval", 5.0)))
            elif action == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        push_task.cancel()
        try:
            await push_task
        except (asyncio.CancelledError, Exception):
            pass
