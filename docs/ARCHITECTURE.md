# Architecture

## High-level

```
                  ┌──────────────────────────┐
   user types ──▶ │   React + Vite frontend  │
   "AAPL"         │   (Tailwind v4 · TS)     │
                  └──────────────┬───────────┘
                                 │  REST + SSE + WebSocket
                  ┌──────────────▼───────────┐
                  │  FastAPI (Python 3.11)   │
                  │  argus.main:app          │
                  └──┬──────────┬────────────┘
                     │          │
        ┌────────────┘          └───────────────┐
        ▼                                        ▼
┌────────────────────┐                ┌──────────────────────────┐
│  market.adapters   │                │  agents.committee        │
│  US (yfinance)     │ ── feeds ──▶   │  Technical · Fundamental │
│  CN (akshare)      │   context      │  Sentiment · Macro · Risk│
│  HK (akshare/yf)   │                │  + CIO orchestrator      │
└────────────────────┘                └──────────┬───────────────┘
                                                 │ uses
                                  ┌──────────────▼─────────────┐
                                  │  agents.llm                │
                                  │  Anthropic / OpenAI /      │
                                  │  DeepSeek / Qwen / Ollama  │
                                  └────────────────────────────┘
```

## Module map

| Path                                  | Purpose                                                     |
| ------------------------------------- | ----------------------------------------------------------- |
| `argus/main.py`                       | FastAPI app, lifespan, route registration, static frontend  |
| `argus/config.py`                     | `Settings` (pydantic-settings) loaded from `.env`           |
| `argus/markets/base.py`               | `MarketAdapter` ABC + `Quote` / `Candle` / `Fundamentals`   |
| `argus/markets/{us,cn,hk}.py`         | Per-market implementations                                  |
| `argus/markets/registry.py`           | Symbol-→-market detection, fanned-out search                |
| `argus/analysis/indicators.py`        | RSI/MACD/BBands/KDJ/ATR/OBV — pandas only, no ta-lib        |
| `argus/analysis/screener.py`          | Cross-market screener with criteria / presets               |
| `argus/agents/llm.py`                 | LLM provider abstraction (streaming-only interface)         |
| `argus/agents/committee.py`           | Six analyst personas + CIO synthesis, async event stream    |
| `argus/analysis/flow.py`              | Smart-money flow aggregator (insider / SI / 北向 / 龙虎榜 / 融资) |
| `argus/storage/db.py`                 | SQLite (SQLModel) — watchlist + alert rules                 |
| `argus/routes/*.py`                   | REST + SSE + WS endpoints                                   |
| `frontend/src/pages/*`                | Dashboard · Stock · Screener · Watchlist · Settings         |
| `frontend/src/components/committee/*` | The visual showpiece — agent cards + verdict card           |

## Data flow — the AI committee

1. UI calls `GET /api/committee/stream/{symbol}` (Server-Sent Events).
2. Backend builds a context bundle (`gather_context`):
   - `quote` + `fundamentals` from the matching market adapter
   - 2-year daily history → indicators (RSI, MACD, BB, KDJ, ATR, OBV)
   - top 5-8 recent headlines
3. Six analyst agents run **concurrently** (capped at `argus_committee_concurrency`, default 3, so free LLM tiers don't drop streams):
   - `Technical` — reads indicator values
   - `Fundamental` — reads valuation + business summary
   - `Sentiment` — reads headlines + recent price ladder
   - `Macro` — places ticker in current macro regime
   - `Risk` — quantifies vol/beta/drawdown, sizes position
   - `Flow` — reads insider trades, short interest, 北向资金, 龙虎榜, 融资余额 — what *smart money* is doing
4. The **CIO** receives every analyst's full text and is asked for **strict JSON**:
   ```json
   { "action": "BUY", "conviction": 4, "horizon": "1-3M",
     "thesis": "...", "key_risks": ["...","..."],
     "entry_zone": "...", "stop_zone": "..." }
   ```
5. SSE emits `agent_start` → `agent_token*` → `agent_done` for each, ending with a `verdict` event.

## Why SSE (not WebSocket) for the committee

SSE is a perfect fit for one-way token streaming, supports reconnection out of the
box, and is trivial to consume in the browser via `EventSource`. WebSocket is reserved
for the bi-directional quote-subscribe channel.

## Adding a new market

1. Subclass `MarketAdapter` in `argus/markets/<m>.py`.
2. Register in `argus/markets/registry._ADAPTERS`.
3. (Optional) extend `detect_market()` heuristics.

## Adding a new agent

1. Add a persona entry to `agents.committee.AGENT_PERSONAS`.
2. Extend `_build_user_prompt()` for that role.
3. Add the role to the loop in `InvestmentCommittee.stream()`.
4. Add a `ROLE_THEME` entry in `frontend/src/components/committee/AgentCard.tsx`.
