"""Multi-agent investment committee.

Five specialised analyst agents debate a ticker, then a Chief Investment Officer
synthesises a final verdict. Output streams as discrete events so the UI can
render each agent's reasoning live.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal

from ..analysis.flow import aggregate_flow
from ..analysis.indicators import compute_indicators, latest_signals
from ..analysis.news import aggregate_news
from ..config import get_settings
from ..markets import detect_market, get_adapter
from ..markets.base import Market
from ..utils import logger
from .llm import LLMClient, Message, get_llm


AgentRole = Literal["technical", "fundamental", "sentiment", "macro", "risk", "flow", "cio"]
Language = Literal["en", "zh"]


# Appended to every agent's system prompt at call time so the analyst writes
# in the user's UI language. CIO is asked to keep JSON keys English while
# putting the prose values (thesis, key_risks) in the chosen language.
LANGUAGE_INSTRUCTIONS: dict[str, dict[Language, str]] = {
    "analyst": {
        "en": "Respond in English.",
        "zh": "请用简体中文回复。术语（如 RSI、MACD、P/E）保留英文缩写。",
    },
    "cio": {
        "en": "Respond in English. JSON keys MUST stay in English exactly as listed.",
        "zh": (
            "JSON 的字段名必须严格保持英文（action / conviction / horizon / "
            "thesis / key_risks / entry_zone / stop_zone）。`thesis` 和 "
            "`key_risks` 的字符串内容请用简体中文。"
        ),
    },
}


AGENT_PERSONAS: dict[AgentRole, dict[str, str]] = {
    "technical": {
        "name": "Technical Analyst",
        "system": (
            "You are a senior technical analyst on a buy-side desk. "
            "Read price action, volume, and momentum / trend / volatility indicators. "
            "Be precise and quantitative. Cite specific indicator readings. "
            "Conclude with a directional view (bullish/neutral/bearish) and a 1-5 conviction score."
        ),
    },
    "fundamental": {
        "name": "Fundamental Analyst",
        "system": (
            "You are a fundamental equity analyst. Evaluate the company on valuation "
            "(P/E, P/B, P/S, dividend yield), profitability, growth, balance-sheet strength, "
            "and competitive moat. Compare to typical sector benchmarks. "
            "Conclude with a fair-value read and a 1-5 conviction score."
        ),
    },
    "sentiment": {
        "name": "Sentiment Analyst",
        "system": (
            "You are a market-sentiment analyst. Read the supplied news headlines and the "
            "recent price/volume action as a proxy for market mood. Identify catalysts, "
            "narrative shifts, crowdedness. Conclude bullish/neutral/bearish + 1-5 conviction."
        ),
    },
    "macro": {
        "name": "Macro Strategist",
        "system": (
            "You are a macro strategist. Place this ticker inside the relevant sector, country, "
            "and macro regime (rates, FX, commodity cycle, geopolitics). Highlight tailwinds and "
            "headwinds. Conclude with a tactical positioning view + 1-5 conviction."
        ),
    },
    "risk": {
        "name": "Risk Manager",
        "system": (
            "You are the desk risk manager. Quantify volatility (ATR, beta), drawdown risk, "
            "liquidity, concentration, regulatory/event risk. Suggest a position-sizing band "
            "(% of book) and a stop-loss zone. Conclude with a 1-5 risk score (5 = highest risk)."
        ),
    },
    "flow": {
        "name": "Flow Analyst",
        "system": (
            "You are a flow & positioning analyst. While the others read price, fundamentals, "
            "sentiment, macro, and risk, you read what the *money* is actually doing — "
            "who is buying or selling, how concentrated, and with how much leverage.\n\n"
            "Watch for:\n"
            "- Insider transactions (Form 4 — cluster buying by execs is a strong signal)\n"
            "- Short interest / days-to-cover (squeeze risk vs broken thesis)\n"
            "- Northbound (Stock Connect) flow for A-shares — foreign smart money\n"
            "- Margin balance (融资余额) trend — retail leverage extremes warn of tops\n"
            "- 龙虎榜 (Dragon-Tiger List) appearances — concentrated single-day flow\n"
            "- Unusual option flow when available\n\n"
            "Cite specific numbers. If a signal is missing for this market, say so explicitly "
            "rather than guess. Conclude with a directional read: smart money is "
            "ACCUMULATING / DISTRIBUTING / NEUTRAL, plus a 1-5 conviction score."
        ),
    },
    "cio": {
        "name": "Chief Investment Officer",
        "system": (
            "You are the CIO synthesising the desk's debate. You receive each analyst's "
            "verdict. Resolve disagreements explicitly, weight by conviction, and produce a "
            "single recommendation.\n\n"
            "Output STRICT JSON with keys:\n"
            "- action: one of BUY | ACCUMULATE | HOLD | TRIM | SELL\n"
            "- conviction: integer 1-5. Calibrate honestly — do not default to 3.\n"
            "    1 = signals contradict outright; recommend stand aside\n"
            "    2 = weak lean, high uncertainty\n"
            "    3 = coherent thesis with real caveats\n"
            "    4 = analysts mostly aligned, supportive setup\n"
            "    5 = strong, near-unanimous setup\n"
            "- horizon: e.g. '1-3M', '3-6M', '6-12M'\n"
            "- thesis: <=80 words. State the actionable read clearly.\n"
            "- key_risks: list of <=3 short bullets\n"
            "- entry_zone: a price range, e.g. '270-282'\n"
            "- stop_zone: a single price or short range"
        ),
    },
}


@dataclass
class CommitteeEvent:
    type: Literal["agent_start", "agent_token", "agent_done", "verdict", "error"]
    role: AgentRole | None = None
    agent_name: str = ""
    text: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "type": self.type,
                "role": self.role,
                "agent_name": self.agent_name,
                "text": self.text,
                "payload": self.payload,
            },
            ensure_ascii=False,
        )


def _fmt_num(v: Any, digits: int = 2) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v):,.{digits}f}"
    except (TypeError, ValueError):
        return str(v)


class InvestmentCommittee:
    def __init__(self, llm: LLMClient | None = None, lang: Language = "en"):
        self.llm = llm or get_llm()
        self.lang = lang if lang in ("en", "zh") else "en"

    def _system_prompt(self, role: AgentRole) -> str:
        base = AGENT_PERSONAS[role]["system"]
        bucket = "cio" if role == "cio" else "analyst"
        return base + "\n\n" + LANGUAGE_INSTRUCTIONS[bucket][self.lang]

    async def gather_context(self, symbol: str, market: Market | None = None) -> dict[str, Any]:
        """Fetch the data each analyst will read.

        Each upstream call is isolated with `return_exceptions=True` so one
        flaky data source never aborts the whole committee. The agents are
        instructed to acknowledge missing data instead of hallucinating.
        """
        resolved_market: Market = market or detect_market(symbol)
        adapter = get_adapter(resolved_market)
        results = await asyncio.gather(
            adapter.quote(symbol),
            adapter.history(symbol, interval="1d"),
            adapter.fundamentals(symbol),
            aggregate_news(symbol, resolved_market, limit=8),
            aggregate_flow(symbol, resolved_market),
            return_exceptions=True,
        )
        quote_r, candles_r, fund_r, news_r, flow_r = results

        # Quote is the only field the rest of the system requires — if even
        # that failed, surface a clear exception rather than silently emit
        # a useless committee.
        if isinstance(quote_r, BaseException):
            raise quote_r

        candles = candles_r if not isinstance(candles_r, BaseException) else []
        fundamentals = fund_r if not isinstance(fund_r, BaseException) else None
        news = news_r if not isinstance(news_r, BaseException) else []
        flow_obj = flow_r if not isinstance(flow_r, BaseException) else None

        if isinstance(candles_r, BaseException):
            logger.warning(f"history fetch failed for {symbol}: {candles_r}")
        if isinstance(fund_r, BaseException):
            logger.warning(f"fundamentals fetch failed for {symbol}: {fund_r}")
        if isinstance(news_r, BaseException):
            logger.warning(f"news fetch failed for {symbol}: {news_r}")
        if isinstance(flow_r, BaseException):
            logger.warning(f"flow fetch failed for {symbol}: {flow_r}")

        ind = compute_indicators(candles[-260:]) if candles else {"latest": {}}
        signals = latest_signals(ind)

        # Build flow + fundamentals dicts even when missing — empty stubs let the
        # prompts safely call .get() instead of branching everywhere.
        from ..analysis.flow import FlowSignals
        from ..markets.base import Fundamentals as FundSchema
        flow_dict = (flow_obj or FlowSignals(market=resolved_market, symbol=symbol,
                                             notes=["flow fetch failed"])).model_dump()
        fund_dict = (fundamentals or FundSchema(symbol=symbol, market=resolved_market,
                                                name="")).model_dump()
        return {
            "quote": quote_r.model_dump(),
            "fundamentals": fund_dict,
            "indicators_latest": ind.get("latest", {}),
            "signals": signals,
            "news": news,
            "flow": flow_dict,
            "candles_summary": _candles_summary(candles),
        }

    def _build_user_prompt(self, role: AgentRole, ctx: dict[str, Any]) -> str:
        q = ctx["quote"]
        f = ctx["fundamentals"]
        latest = ctx["indicators_latest"]
        signals = ctx["signals"]
        news = ctx["news"][:5]
        common = (
            f"Ticker: {q['symbol']} ({f.get('name') or q.get('name')})\n"
            f"Market: {q['market']}  Currency: {q['currency']}\n"
            f"Last: {_fmt_num(q['price'])}  Δ%: {_fmt_num(q['change_pct'])}  "
            f"Mkt cap: {_fmt_num(q.get('market_cap'), 0)}\n"
        )

        if role == "technical":
            return (
                common
                + "\n--- Indicators (latest) ---\n"
                + f"RSI(14): {_fmt_num(latest.get('rsi_14'))}\n"
                + f"MACD/Signal: {_fmt_num(latest.get('macd'))} / {_fmt_num(latest.get('macd_signal'))}\n"
                + f"SMA20/50/200: {_fmt_num(latest.get('sma_20'))} / {_fmt_num(latest.get('sma_50'))} / {_fmt_num(latest.get('sma_200'))}\n"
                + f"BB(upper/mid/lower): {_fmt_num(latest.get('bb_upper'))} / {_fmt_num(latest.get('bb_mid'))} / {_fmt_num(latest.get('bb_lower'))}\n"
                + f"KDJ K/D/J: {_fmt_num(latest.get('kdj_k'))} / {_fmt_num(latest.get('kdj_d'))} / {_fmt_num(latest.get('kdj_j'))}\n"
                + f"ATR(14): {_fmt_num(latest.get('atr_14'))}\n"
                + f"Quick read: {signals}\n\n"
                + f"Recent close ladder: {ctx['candles_summary']}\n\n"
                + "Write 4-6 sentences of technical commentary, then a one-line verdict."
            )

        if role == "fundamental":
            return (
                common
                + f"\nSector: {f.get('sector')}  Industry: {f.get('industry')}\n"
                + f"P/E (trailing/forward): {_fmt_num(f.get('pe_ratio'))} / {_fmt_num(f.get('forward_pe'))}\n"
                + f"P/B: {_fmt_num(f.get('pb_ratio'))}  P/S: {_fmt_num(f.get('ps_ratio'))}  Div yield: {_fmt_num(f.get('dividend_yield'), 4)}\n"
                + f"EPS (TTM): {_fmt_num(f.get('eps'))}  Profit margin: {_fmt_num(f.get('profit_margin'), 4)}  Beta: {_fmt_num(f.get('beta'))}\n"
                + f"52W high/low: {_fmt_num(f.get('fifty_two_week_high'))} / {_fmt_num(f.get('fifty_two_week_low'))}\n"
                + f"Business: {(f.get('summary') or '')[:600]}\n\n"
                + "Write 4-6 sentences of fundamental commentary, then a one-line verdict with fair-value read."
            )

        if role == "sentiment":
            news_block = "\n".join(f"• {n['title']} ({n.get('publisher','')})" for n in news) or "No news fetched."
            return (
                common
                + "\n--- Recent headlines ---\n"
                + news_block
                + f"\n\n5-day price action: {ctx['candles_summary']}\n\n"
                + "Write 4-6 sentences on sentiment / narrative, then a one-line verdict."
            )

        if role == "macro":
            return (
                common
                + f"\nSector: {f.get('sector')}  Industry: {f.get('industry')}\n"
                + f"Beta: {_fmt_num(f.get('beta'))}\n\n"
                + "Place this ticker in the prevailing macro regime (rates / dollar / China demand / "
                + "AI capex / geopolitics, etc — pick the most relevant 2-3). 4-6 sentences then a verdict."
            )

        if role == "risk":
            return (
                common
                + f"\nATR(14): {_fmt_num(latest.get('atr_14'))}  Beta: {_fmt_num(f.get('beta'))}\n"
                + f"52W range: {_fmt_num(f.get('fifty_two_week_low'))} – {_fmt_num(f.get('fifty_two_week_high'))}\n\n"
                + "Quantify the risk profile and propose a position-sizing band + stop-loss zone. "
                + "4-6 sentences, then a 1-5 risk score."
            )

        if role == "flow":
            flow = ctx.get("flow") or {}
            market = q["market"]
            blocks: list[str] = [common, ""]
            if market == "US":
                blocks.append("--- Insider transactions (Finnhub, last 90d) ---")
                txns = flow.get("insider_transactions") or []
                if txns:
                    blocks.append(
                        f"Net buys − sells: {flow.get('insider_net_buy_count', 0)}; "
                        f"Net $ value: {_fmt_num(flow.get('insider_net_buy_value'), 0)}"
                    )
                    for t in txns[:6]:
                        blocks.append(
                            f"  {t.get('date')} · {t.get('name','')[:30]:<30} "
                            f"{t.get('type')} {_fmt_num(t.get('shares'), 0)} sh"
                        )
                else:
                    blocks.append("(no recent insider activity reported / no Finnhub key)")
                blocks.append("")
                blocks.append("--- Short interest ---")
                blocks.append(
                    f"% of float: {_fmt_num(flow.get('short_pct_float'))}%   "
                    f"days-to-cover: {_fmt_num(flow.get('short_ratio_dtc'))}"
                )
            elif market == "CN":
                blocks.append("--- 龙虎榜 (recent) ---")
                lhb = flow.get("lhb_recent") or []
                if lhb:
                    for entry in lhb[:5]:
                        blocks.append(
                            f"  {entry.get('date')} · {entry.get('reason','')[:40]} · "
                            f"净买入 ¥{_fmt_num(entry.get('net_buy_amount'), 0)}"
                        )
                else:
                    blocks.append("(no recent dragon-tiger appearances)")
                blocks.append("")
                nb = flow.get("northbound_5d_net_cny")
                blocks.append(
                    f"--- 北向资金 5日净流入: ¥{_fmt_num(nb, 0) if nb is not None else 'n/a'} ---"
                )
                margin = flow.get("margin_balance_5d_change_pct")
                blocks.append(
                    f"--- 融资余额 5日变化: "
                    f"{_fmt_num(margin) + '%' if margin is not None else '(not yet wired in v1)'} ---"
                )
            elif market == "HK":
                blocks.append("--- HK flow data ---")
                blocks.append("(HK flow signals not yet wired in this version; "
                              "make a directional read from the price/volume context only.)")
            notes = flow.get("notes") or []
            if notes:
                blocks.append("")
                blocks.append(f"Adapter notes: {'; '.join(notes)[:300]}")
            blocks.append("")
            blocks.append(
                "Write 4-6 sentences. State explicitly which signals were available "
                "and which weren't, then conclude: ACCUMULATING / DISTRIBUTING / NEUTRAL, "
                "with a 1-5 conviction score."
            )
            return "\n".join(blocks)

        return ""  # cio handled separately

    async def _run_agent(
        self, role: AgentRole, ctx: dict[str, Any]
    ) -> AsyncIterator[CommitteeEvent]:
        persona = AGENT_PERSONAS[role]
        agent_name = persona["name"]
        yield CommitteeEvent(type="agent_start", role=role, agent_name=agent_name)
        messages = [
            Message(role="system", content=self._system_prompt(role)),
            Message(role="user", content=self._build_user_prompt(role, ctx)),
        ]
        full = []
        try:
            async for delta in self.llm.astream(messages):
                full.append(delta)
                yield CommitteeEvent(type="agent_token", role=role, agent_name=agent_name, text=delta)
        except Exception as e:
            logger.exception(f"agent {role} failed")
            yield CommitteeEvent(type="error", role=role, agent_name=agent_name, text=str(e))
            return
        yield CommitteeEvent(
            type="agent_done", role=role, agent_name=agent_name,
            payload={"summary": "".join(full)},
        )

    async def _run_cio(
        self, ctx: dict[str, Any], analyst_outputs: dict[AgentRole, str]
    ) -> AsyncIterator[CommitteeEvent]:
        persona = AGENT_PERSONAS["cio"]
        agent_name = persona["name"]
        yield CommitteeEvent(type="agent_start", role="cio", agent_name=agent_name)

        # Truncate each analyst's contribution so the CIO prompt stays
        # manageable. Free-tier providers (NVIDIA NIM in particular) drop
        # long streams; a tighter input meaningfully lowers that risk and
        # the CIO is supposed to synthesise, not transcribe.
        MAX_PER_ANALYST = 800
        truncated = {
            r: (txt if len(txt) <= MAX_PER_ANALYST else txt[:MAX_PER_ANALYST] + "…")
            for r, txt in analyst_outputs.items()
        }
        contributing = [AGENT_PERSONAS[r]["name"] for r in truncated]
        all_analysts = ["technical", "fundamental", "sentiment", "macro", "risk", "flow"]
        missing = [
            AGENT_PERSONAS[r]["name"]  # type: ignore[index]
            for r in all_analysts if r not in truncated
        ]
        debate_block = "\n\n".join(
            f"### {AGENT_PERSONAS[r]['name']}\n{txt}" for r, txt in truncated.items()
        )
        q = ctx["quote"]
        contrib_line = f"Analysts contributing: {', '.join(contributing) or '(none)'}"
        if missing:
            contrib_line += f"\nAnalysts UNAVAILABLE this run: {', '.join(missing)} — discount conviction accordingly."
        user = (
            f"Ticker: {q['symbol']} {ctx['fundamentals'].get('name','')} "
            f"@ {_fmt_num(q['price'])} {q['currency']}\n"
            f"{contrib_line}\n\n"
            f"=== Analyst Debate ===\n{debate_block}\n\n"
            "Synthesise. Output STRICT JSON only — no prose, no code fences."
        )
        messages = [
            Message(role="system", content=self._system_prompt("cio")),
            Message(role="user", content=user),
        ]

        # Retry once on transport-level failures. The CIO call is the longest
        # streaming response in the run; NVIDIA NIM free tier closes such
        # connections mid-flight from time to time and a fresh connection
        # usually succeeds.
        MAX_ATTEMPTS = 2
        last_exc: Exception | None = None
        full: list[str] = []
        for attempt in range(MAX_ATTEMPTS):
            full = []
            try:
                async for delta in self.llm.astream(messages):
                    full.append(delta)
                    yield CommitteeEvent(
                        type="agent_token", role="cio",
                        agent_name=agent_name, text=delta,
                    )
                last_exc = None
                break  # streamed successfully
            except Exception as e:
                last_exc = e
                logger.warning(
                    f"CIO attempt {attempt + 1}/{MAX_ATTEMPTS} failed: {e}"
                )
                if attempt + 1 < MAX_ATTEMPTS:
                    # Brief pause + reset the UI's partial CIO text so the
                    # retry's tokens accumulate cleanly. agent_start sets
                    # status=thinking and clears the text buffer in the store.
                    await asyncio.sleep(2.0)
                    yield CommitteeEvent(type="agent_start", role="cio", agent_name=agent_name)

        if last_exc is not None:
            logger.exception("cio failed after retries", exc_info=last_exc)
            yield CommitteeEvent(
                type="error", role="cio", agent_name=agent_name,
                text=f"{last_exc} (after {MAX_ATTEMPTS} attempts)",
            )
            return

        raw = "".join(full).strip()
        verdict = _safe_json(raw)
        yield CommitteeEvent(type="agent_done", role="cio", agent_name=agent_name, payload={"raw": raw})
        yield CommitteeEvent(type="verdict", payload=verdict)

    async def stream(
        self, symbol: str, market: Market | None = None
    ) -> AsyncIterator[CommitteeEvent]:
        ctx = await self.gather_context(symbol, market)
        analyst_roles: tuple[AgentRole, ...] = (
            "technical", "fundamental", "sentiment", "macro", "risk", "flow",
        )
        analyst_outputs: dict[AgentRole, str] = {}

        # Run analysts CONCURRENTLY — they read disjoint data slices so
        # there's no reason to serialise them. The semaphore caps how many
        # the LLM provider sees at once; 3 is safe on most free tiers.
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL = object()
        cap = max(1, get_settings().argus_committee_concurrency)
        sem = asyncio.Semaphore(cap)

        async def run_one(role: AgentRole) -> None:
            buf: list[str] = []
            try:
                async with sem:
                    async for ev in self._run_agent(role, ctx):
                        if ev.type == "agent_token":
                            buf.append(ev.text)
                        elif ev.type == "agent_done":
                            analyst_outputs[role] = "".join(buf)
                        await queue.put(ev)
            finally:
                await queue.put((SENTINEL, role))

        tasks = [asyncio.create_task(run_one(r)) for r in analyst_roles]
        pending: set[AgentRole] = set(analyst_roles)

        try:
            while pending:
                item = await queue.get()
                if isinstance(item, tuple) and item and item[0] is SENTINEL:
                    pending.discard(item[1])  # type: ignore[arg-type]
                    continue
                yield item  # CommitteeEvent
        finally:
            # Client disconnect / generator close — don't leak the tasks.
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        # CIO must wait for all analysts to settle before synthesising.
        async for ev in self._run_cio(ctx, analyst_outputs):
            yield ev


def _candles_summary(candles: list) -> str:
    if not candles:
        return "no history"
    last = candles[-5:]
    return ", ".join(f"{c.time.strftime('%m-%d')}={c.close:.2f}" for c in last)


def _safe_json(raw: str) -> dict[str, Any]:
    """Robustly extract JSON from a possibly noisy LLM response."""
    raw = raw.strip()
    if raw.startswith("```"):
        # strip code fences
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        if raw.endswith("```"):
            raw = raw[:-3]
    # Find first '{' .. matching '}'
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return {"raw": raw}
    blob = raw[start : end + 1]
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return {"raw": raw}
