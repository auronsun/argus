"""Smoke tests for premium-data-source API keys.

Each provider gets one cheap, well-defined call. Errors are mapped to the
same `kind` taxonomy the LLM smoke test uses, so the frontend renders
both classes of result with one component.
"""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ..config import get_settings
from ..storage import secrets


# Slots that have a real implemented smoke test. Longbridge is intentionally
# excluded — its auth requires SDK-side request signing, not a single GET.
DATA_SLOTS = ("finnhub", "alpha_vantage", "tushare")


def _truncate(s: str, n: int = 220) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _no_key(provider: str) -> dict[str, Any]:
    return {"ok": False, "kind": "no_key", "provider": provider,
            "detail": "Key not configured for this provider."}


def _classify_http(status: int, text: str) -> str:
    low = (text or "").lower()
    if status in (401, 403) or "unauthorized" in low or "forbidden" in low or "invalid" in low and "key" in low:
        return "auth"
    if status == 404:
        return "model_not_found"
    if status == 429 or "rate" in low and "limit" in low:
        return "rate_limit"
    return "unknown"


async def smoke_test_data(slot: str, timeout: float = 15.0) -> dict[str, Any]:
    s = get_settings()
    if slot == "finnhub":
        key = secrets.effective("finnhub", s.finnhub_api_key)
        if not key:
            return _no_key("finnhub")
        return await _smoke_finnhub(key, timeout)
    if slot == "alpha_vantage":
        key = secrets.effective("alpha_vantage", s.alpha_vantage_api_key)
        if not key:
            return _no_key("alpha_vantage")
        return await _smoke_alpha_vantage(key, timeout)
    if slot == "tushare":
        token = secrets.effective("tushare", s.tushare_token)
        if not token:
            return _no_key("tushare")
        return await _smoke_tushare(token, timeout)
    return {"ok": False, "kind": "unknown", "provider": slot,
            "detail": f"Smoke test not implemented for slot '{slot}'."}


# ----------------------------------------------------------------------------
# Per-provider implementations
# ----------------------------------------------------------------------------

async def _smoke_finnhub(key: str, timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": "AAPL", "token": key},
            )
    except httpx.TimeoutException:
        return {"ok": False, "kind": "timeout", "provider": "finnhub",
                "detail": f"No response within {int(timeout)}s."}
    except httpx.RequestError as e:
        return {"ok": False, "kind": "network", "provider": "finnhub", "detail": _truncate(str(e))}

    latency = int((time.monotonic() - started) * 1000)
    if r.status_code >= 400:
        return {"ok": False, "kind": _classify_http(r.status_code, r.text),
                "provider": "finnhub", "detail": _truncate(r.text)}

    try:
        body = r.json()
    except json.JSONDecodeError:
        return {"ok": False, "kind": "unknown", "provider": "finnhub",
                "detail": "Response was not valid JSON."}

    if not isinstance(body, dict) or "c" not in body:
        return {"ok": False, "kind": "auth", "provider": "finnhub",
                "detail": _truncate(json.dumps(body))}
    return {"ok": True, "kind": "ok", "latency_ms": latency, "provider": "finnhub",
            "sample": f"AAPL last = ${body.get('c')}"}


async def _smoke_alpha_vantage(key: str, timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(
                "https://www.alphavantage.co/query",
                params={"function": "GLOBAL_QUOTE", "symbol": "AAPL", "apikey": key},
            )
    except httpx.TimeoutException:
        return {"ok": False, "kind": "timeout", "provider": "alpha_vantage",
                "detail": f"No response within {int(timeout)}s."}
    except httpx.RequestError as e:
        return {"ok": False, "kind": "network", "provider": "alpha_vantage",
                "detail": _truncate(str(e))}

    latency = int((time.monotonic() - started) * 1000)
    if r.status_code >= 400:
        return {"ok": False, "kind": _classify_http(r.status_code, r.text),
                "provider": "alpha_vantage", "detail": _truncate(r.text)}

    try:
        body = r.json()
    except json.JSONDecodeError:
        return {"ok": False, "kind": "unknown", "provider": "alpha_vantage",
                "detail": "Response was not valid JSON."}

    if "Error Message" in body:
        return {"ok": False, "kind": "auth", "provider": "alpha_vantage",
                "detail": _truncate(body["Error Message"])}
    if "Note" in body or "Information" in body:
        # AV uses these for both rate-limit and explanatory messages
        return {"ok": False, "kind": "rate_limit", "provider": "alpha_vantage",
                "detail": _truncate(body.get("Note") or body.get("Information"))}
    quote = body.get("Global Quote")
    if not quote:
        return {"ok": False, "kind": "unknown", "provider": "alpha_vantage",
                "detail": _truncate(json.dumps(body))}
    price = quote.get("05. price")
    return {"ok": True, "kind": "ok", "latency_ms": latency, "provider": "alpha_vantage",
            "sample": f"AAPL last = ${price}"}


async def _smoke_tushare(token: str, timeout: float) -> dict[str, Any]:
    """Tushare Pro uses a single POST with token in the body."""
    started = time.monotonic()
    body = {
        "api_name": "trade_cal",
        "token": token,
        "params": {"exchange": "SSE", "start_date": "20240102", "end_date": "20240105"},
        "fields": "cal_date,is_open",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post("http://api.tushare.pro", json=body)
    except httpx.TimeoutException:
        return {"ok": False, "kind": "timeout", "provider": "tushare",
                "detail": f"No response within {int(timeout)}s."}
    except httpx.RequestError as e:
        return {"ok": False, "kind": "network", "provider": "tushare", "detail": _truncate(str(e))}

    latency = int((time.monotonic() - started) * 1000)
    try:
        payload = r.json()
    except json.JSONDecodeError:
        return {"ok": False, "kind": "unknown", "provider": "tushare",
                "detail": _truncate(r.text)}

    code = payload.get("code")
    msg = payload.get("msg") or ""
    if code == 0:
        rows = ((payload.get("data") or {}).get("items") or [])
        return {"ok": True, "kind": "ok", "latency_ms": latency, "provider": "tushare",
                "sample": f"trade_cal returned {len(rows)} row(s)"}
    # Tushare returns 40001/40002 etc for token / permission errors
    kind = "auth"
    if "频" in msg or "次数" in msg or "limit" in msg.lower() or "频率" in msg:
        kind = "rate_limit"
    return {"ok": False, "kind": kind, "provider": "tushare", "detail": _truncate(msg or str(payload))}
