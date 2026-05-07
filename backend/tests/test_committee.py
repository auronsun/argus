"""Committee streaming tests with a fake adapter and the built-in MockClient.
No network calls. No real LLM calls.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from argus.agents import llm as llm_mod
from argus.agents.committee import InvestmentCommittee
from argus.agents.llm import MockClient
from argus.markets import registry as registry_mod
from argus.markets.base import Candle, Fundamentals, Quote, SymbolSearchResult


class _FakeAdapter:
    market = "US"

    def normalize(self, s: str) -> str:
        return s.upper()

    async def quote(self, symbol):
        return Quote(symbol="AAPL", market="US", name="Apple Inc.", price=200.0,
                     change=1.0, change_pct=0.5, currency="USD")

    async def history(self, symbol, interval="1d", start=None, end=None):
        out = []
        price = 100.0
        for _ in range(60):
            price *= 1.005
            out.append(Candle(time=datetime(2024, 1, 1), open=price, high=price * 1.01,
                              low=price * 0.99, close=price, volume=1_000_000))
        return out

    async def fundamentals(self, symbol):
        return Fundamentals(symbol="AAPL", market="US", name="Apple Inc.",
                            sector="Technology", industry="Consumer Electronics",
                            market_cap=3.0e12, currency="USD", pe_ratio=30.0,
                            beta=1.2)

    async def search(self, query, limit=10):
        return [SymbolSearchResult(symbol="AAPL", name="Apple Inc.", market="US",
                                   exchange="NASDAQ")]

    async def news(self, symbol, limit=10):
        return [{"title": "Apple ships new product", "publisher": "Reuters",
                 "url": "https://example.com/a", "published": "2024-01-01", "summary": ""}]


@pytest.fixture
def fake_adapter(monkeypatch):
    fa = _FakeAdapter()
    # Replace the registry's lookup for any input.
    monkeypatch.setattr(registry_mod, "get_adapter", lambda *a, **k: fa)
    # The committee imports get_adapter from `..markets`, which re-exports it; patch both.
    import argus.agents.committee as cm
    monkeypatch.setattr(cm, "get_adapter", lambda *a, **k: fa)

    # aggregate_flow goes around the adapter (it talks to yfinance / Finnhub /
    # akshare directly), so we have to stub it independently to keep tests
    # off-network. Empty signals are fine — the Flow Analyst will just say so.
    from argus.analysis.flow import FlowSignals
    async def _empty_flow(symbol, market):
        return FlowSignals(market=market, symbol=symbol,
                           notes=["test stub: no flow signals available"])
    monkeypatch.setattr(cm, "aggregate_flow", _empty_flow)

    return fa


@pytest.mark.asyncio
async def test_committee_streams_full_event_sequence(fake_adapter):
    committee = InvestmentCommittee(llm=MockClient())
    events = []
    async for ev in committee.stream("AAPL"):
        events.append(ev)
        # Sanity: enough events to demonstrate streaming, but bounded.
        if len(events) > 500:
            break

    types = [e.type for e in events]
    # Six analysts (technical/fundamental/sentiment/macro/risk/flow) + cio.
    assert types.count("agent_start") == 7
    assert types.count("agent_done") == 7
    assert "agent_token" in types
    # Final synthesis event:
    assert "verdict" in types

    # Each analyst role must have fired exactly one start event.
    started_roles = [e.role for e in events if e.type == "agent_start"]
    assert set(started_roles) == {
        "technical", "fundamental", "sentiment", "macro", "risk", "flow", "cio",
    }

    # Verdict event has no role (it is the final synthesis), and a payload dict.
    verdict = next(e for e in events if e.type == "verdict")
    assert verdict.role is None
    assert isinstance(verdict.payload, dict)


# ----------------------------------------------------------------------------
# Language directive plumbing
# ----------------------------------------------------------------------------

class _CapturingClient:
    """Captures every list of messages it was sent. Yields a tiny stream so
    the committee proceeds to the next agent."""
    provider = "capture"
    model = "capture-model"

    def __init__(self):
        self.captured: list[list] = []

    async def astream(self, messages):
        self.captured.append(list(messages))
        for chunk in ("o", "k"):
            yield chunk


@pytest.mark.asyncio
async def test_lang_zh_injects_chinese_instruction(fake_adapter):
    cap = _CapturingClient()
    committee = InvestmentCommittee(llm=cap, lang="zh")
    async for _ in committee.stream("AAPL"):
        pass

    assert cap.captured, "expected at least one LLM call"
    sys_msg = cap.captured[0][0]  # first agent's system prompt
    assert sys_msg.role == "system"
    assert "中文" in sys_msg.content

    # CIO is the last call; must keep JSON keys in English.
    cio_sys = cap.captured[-1][0]
    assert cio_sys.role == "system"
    assert "JSON" in cio_sys.content
    assert "字段名" in cio_sys.content  # the Chinese CIO directive


@pytest.mark.asyncio
async def test_lang_en_does_not_inject_chinese(fake_adapter):
    cap = _CapturingClient()
    committee = InvestmentCommittee(llm=cap, lang="en")
    async for _ in committee.stream("AAPL"):
        pass

    sys_msg = cap.captured[0][0]
    assert "中文" not in sys_msg.content
    assert "Respond in English" in sys_msg.content


# ----------------------------------------------------------------------------
# Per-agent retry
# ----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_single_analyst_reruns_only_that_role_plus_cio(fake_adapter):
    """stream_retry should fire agent_start + agent_done for the requested
    role, then for cio. NOT for the other 5 analysts."""
    cap = _CapturingClient()
    committee = InvestmentCommittee(llm=cap, lang="en")
    events = []
    existing = {
        "technical": "previous technical output",
        "fundamental": "previous fundamental output",
        "sentiment": "previous sentiment output",
        "macro": "previous macro output",
        "flow": "previous flow output",
    }
    async for ev in committee.stream_retry(
        "AAPL", role="risk", existing_outputs=existing,
    ):
        events.append(ev)

    started = [e.role for e in events if e.type == "agent_start"]
    assert started == ["risk", "cio"], f"got {started}"
    # Only TWO LLM calls were issued (risk + cio), not seven.
    assert len(cap.captured) == 2

    # Last call (cio) must include the supplied existing outputs verbatim.
    cio_user_msg = cap.captured[-1][1].content
    for prior in existing.values():
        assert prior in cio_user_msg


@pytest.mark.asyncio
async def test_retry_cio_only_skips_analyst_call(fake_adapter):
    """When role='cio', no analyst is rerun — only CIO."""
    cap = _CapturingClient()
    committee = InvestmentCommittee(llm=cap, lang="en")
    events = []
    async for ev in committee.stream_retry(
        "AAPL", role="cio",
        existing_outputs={"technical": "t", "fundamental": "f", "sentiment": "s",
                          "macro": "m", "risk": "r", "flow": "fl"},
    ):
        events.append(ev)

    started = [e.role for e in events if e.type == "agent_start"]
    assert started == ["cio"]
    assert len(cap.captured) == 1


@pytest.mark.asyncio
async def test_retry_unknown_role_raises():
    committee = InvestmentCommittee(llm=_CapturingClient(), lang="en")
    with pytest.raises(ValueError):
        async for _ in committee.stream_retry("AAPL", role="bogus", existing_outputs={}):  # type: ignore[arg-type]
            pass
