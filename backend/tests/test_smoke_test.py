"""Tests for the /api/settings/test/{slot} smoke-test endpoint.
All hermetic — no real LLM/network calls.
"""
from __future__ import annotations

from typing import AsyncIterator

from fastapi.testclient import TestClient

from argus.agents import llm_test
from argus.agents.llm import LLMClient, Message, MockClient
from argus.main import app


client = TestClient(app)


# ---- shape / routing -------------------------------------------------------

def test_unknown_slot_returns_404():
    r = client.post("/api/settings/test/no-such-slot")
    assert r.status_code == 404


def test_unconfigured_provider_returns_no_key(monkeypatch):
    """If build_llm_for returns None, the endpoint surfaces kind=no_key."""
    monkeypatch.setattr(llm_test, "build_llm_for", lambda provider: None)
    r = client.post("/api/settings/test/openai")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["kind"] == "no_key"
    # Never leak any secret material in the body
    assert "api_key" not in r.text.lower() or "api_key" in body["detail"].lower()  # detail may *describe* keys


# ---- success path with MockClient ------------------------------------------

def test_mock_client_smoke_test_succeeds(monkeypatch):
    """A MockClient yields canned tokens; the endpoint should report ok=true
    with a latency_ms and a sample. Exercises the streaming path end-to-end
    without any network."""
    monkeypatch.setattr(llm_test, "build_llm_for", lambda provider: MockClient())
    r = client.post("/api/settings/test/openai")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["kind"] == "ok"
    assert isinstance(body["latency_ms"], int) and body["latency_ms"] >= 0
    assert body["provider"] == "openai"
    assert body["model"]  # MockClient has a model name
    assert body["sample"]  # at least one chunk got through


# ---- failure classification ------------------------------------------------

class _FailingClient(LLMClient):
    """LLMClient that raises a chosen exception once .astream() is iterated."""

    provider = "test"
    model = "test-model"

    def __init__(self, exc: Exception):
        self._exc = exc

    async def astream(self, messages: list[Message]) -> AsyncIterator[str]:
        raise self._exc
        # Make this a generator (unreachable yield):
        yield ""  # pragma: no cover


def _expect_kind(monkeypatch, exc: Exception, kind: str):
    monkeypatch.setattr(llm_test, "build_llm_for", lambda provider: _FailingClient(exc))
    r = client.post("/api/settings/test/openai")
    body = r.json()
    assert body["ok"] is False, body
    assert body["kind"] == kind, body
    return body


def test_classifies_auth_error(monkeypatch):
    _expect_kind(monkeypatch, RuntimeError("401 Unauthorized: invalid_api_key"), "auth")


def test_classifies_model_not_found(monkeypatch):
    _expect_kind(monkeypatch, RuntimeError("404 The model 'gpt-9.0' does not exist"), "model_not_found")


def test_classifies_rate_limit(monkeypatch):
    _expect_kind(monkeypatch, RuntimeError("429 rate_limit_exceeded"), "rate_limit")


def test_classifies_unknown_error(monkeypatch):
    body = _expect_kind(monkeypatch, RuntimeError("something weird"), "unknown")
    # detail is surfaced (truncated)
    assert "weird" in body["detail"]
