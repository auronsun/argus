"""HTTP-level tests using FastAPI's TestClient. No network calls."""
from __future__ import annotations

from fastapi.testclient import TestClient

from argus.main import app


client = TestClient(app)


# ---- system ----------------------------------------------------------------

def test_health():
    r = client.get("/api/system/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "version" in body


def test_capabilities_shape():
    r = client.get("/api/system/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert set(body["markets"]) == {"US", "CN", "HK"}
    assert "available" in body["llm"]
    # nvidia is the new provider added in this revision
    assert "nvidia" in body["llm"]["available"]


# ---- screener --------------------------------------------------------------

def test_screener_unknown_preset_returns_404():
    r = client.get("/api/screener/preset/no-such-preset")
    assert r.status_code == 404
    assert "unknown preset" in r.json()["detail"]


def test_screener_presets_lists_known_keys():
    r = client.get("/api/screener/presets")
    assert r.status_code == 200
    keys = set(r.json()["presets"])
    assert {"momentum", "oversold", "all"}.issubset(keys)


def test_screener_run_validates_bounds():
    """rsi_above must be 0..100; -1 should be 422."""
    r = client.post("/api/screener/run", json={"rsi_above": -1, "limit": 1})
    assert r.status_code == 422


def test_screener_run_caps_limit():
    """limit > 200 must be rejected."""
    r = client.post("/api/screener/run", json={"limit": 9999})
    assert r.status_code == 422


# ---- watchlist alerts ------------------------------------------------------

def test_alert_invalid_metric_rejected():
    r = client.post("/api/watchlist/alerts", json={
        "symbol": "AAPL", "metric": "evil", "op": ">", "threshold": 1.0,
    })
    assert r.status_code == 422


def test_alert_invalid_op_rejected():
    r = client.post("/api/watchlist/alerts", json={
        "symbol": "AAPL", "metric": "price", "op": "BAD", "threshold": 1.0,
    })
    assert r.status_code == 422


def test_alert_valid_payload_accepted():
    r = client.post("/api/watchlist/alerts", json={
        "symbol": "AAPL", "metric": "rsi_14", "op": ">=", "threshold": 70,
    })
    assert r.status_code == 200
    rule = r.json()["alert"]
    assert rule["metric"] == "rsi_14"
    assert rule["op"] == ">="
    # cleanup
    client.delete(f"/api/watchlist/alerts/{rule['id']}")


# ---- settings (keys API) ---------------------------------------------------

def test_settings_keys_roundtrip_does_not_leak_value():
    """We can save a key and observe it as configured, without the value
    ever being returned over the API."""
    r = client.post("/api/settings/keys", json={"updates": {"nvidia": "nvapi-test-fake"}})
    assert r.status_code == 200
    body = r.json()
    assert body["providers"]["nvidia"]["configured"] is True
    # response must not echo the key anywhere
    assert "nvapi-test-fake" not in r.text

    caps = client.get("/api/system/capabilities").json()
    assert caps["llm"]["provider"] == "nvidia"

    # cleanup
    client.delete("/api/settings/keys/nvidia")
    after = client.get("/api/settings/keys").json()
    assert after["providers"]["nvidia"]["configured"] is False


def test_settings_unknown_slot_silently_ignored():
    """Unknown slot names must not write anything; valid slots in the
    same payload should still apply."""
    r = client.post("/api/settings/keys", json={
        "updates": {"unknown_slot": "x", "openai": "sk-test-fake"}
    })
    assert r.status_code == 200
    body = r.json()
    assert "unknown_slot" not in body["providers"]
    assert body["providers"]["openai"]["configured"] is True
    client.delete("/api/settings/keys/openai")


# ---- market route input validation ----------------------------------------

def test_search_query_required():
    r = client.get("/api/market/search")
    assert r.status_code == 422


def test_indicators_lookback_bounds():
    """lookback < 60 should be rejected without ever calling an adapter."""
    r = client.get("/api/analysis/indicators/AAPL?lookback=10")
    assert r.status_code == 422
