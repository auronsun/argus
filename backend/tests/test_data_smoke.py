"""Tests for data-source smoke tests. Hermetic — no real network."""
from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from argus.agents import data_test
from argus.main import app
from argus.storage import secrets


client = TestClient(app)


# ---- routing dispatch ------------------------------------------------------

def test_unknown_data_slot_returns_404():
    r = client.post("/api/settings/test/no-such-data")
    assert r.status_code == 404


def test_longbridge_is_not_smoke_testable():
    """We deliberately don't expose a smoke test for Longbridge yet (its
    auth needs SDK signing). The route should 404, never crash."""
    r = client.post("/api/settings/test/longbridge_token")
    assert r.status_code == 404


def test_finnhub_no_key_returns_no_key():
    secrets.clear("finnhub")
    r = client.post("/api/settings/test/finnhub")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["kind"] == "no_key"
    assert body["provider"] == "finnhub"


# ---- happy path: monkeypatch the per-provider function --------------------

def test_finnhub_dispatches_to_data_test(monkeypatch):
    """When a key is set, the route reaches _smoke_finnhub. Patch that
    function to return a fixed payload, assert the dispatcher calls it."""
    captured: dict[str, Any] = {}

    async def fake(key: str, timeout: float):
        captured["key"] = key
        return {"ok": True, "kind": "ok", "latency_ms": 7,
                "provider": "finnhub", "sample": "AAPL last = $200.00"}

    secrets.set_many({"finnhub": "fnh-test-key-abc"})
    monkeypatch.setattr(data_test, "_smoke_finnhub", fake)

    r = client.post("/api/settings/test/finnhub")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["sample"].startswith("AAPL last")
    assert captured["key"] == "fnh-test-key-abc"

    secrets.clear("finnhub")


def test_alpha_vantage_classifies_rate_limit(monkeypatch):
    """When AV returns a 'Note' field (their rate-limit signal), we report
    kind=rate_limit, not auth/unknown."""
    class _FakeResp:
        status_code = 200
        text = '{"Note":"limit"}'
        def json(self):
            return {"Note": "Thank you for using Alpha Vantage! Please subscribe…"}

    class _FakeClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **kw): return _FakeResp()

    import argus.agents.data_test as dt
    monkeypatch.setattr(dt.httpx, "AsyncClient", _FakeClient)
    secrets.set_many({"alpha_vantage": "av-test"})

    r = client.post("/api/settings/test/alpha_vantage")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["kind"] == "rate_limit"

    secrets.clear("alpha_vantage")


def test_tushare_classifies_auth(monkeypatch):
    """Tushare returns code != 0 with a Chinese message for bad token."""
    class _FakeResp:
        status_code = 200
        def json(self):
            return {"code": 40001, "msg": "无效的token"}

    class _FakeClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **kw): return _FakeResp()

    import argus.agents.data_test as dt
    monkeypatch.setattr(dt.httpx, "AsyncClient", _FakeClient)
    secrets.set_many({"tushare": "ts-test"})

    r = client.post("/api/settings/test/tushare")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["kind"] == "auth"
    assert "无效" in body["detail"]

    secrets.clear("tushare")
