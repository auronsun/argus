<div align="center">

# Argus

### Watch every market with a hundred eyes.

An open-source AI **investment committee** for US stocks, A-shares, and Hong Kong stocks.
Six specialised analyst agents — including a dedicated **Flow Analyst** that reads
insider trades, short interest, northbound flow, and the dragon-tiger list —
debate a ticker in real time and a Chief Investment Officer synthesises
the verdict, all streamed to a glass-morphism web UI.

[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776ab.svg)](https://www.python.org)
[![React 18](https://img.shields.io/badge/react-18-61dafb.svg)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![Tailwind v4](https://img.shields.io/badge/Tailwind-v4-38bdf8.svg)](https://tailwindcss.com)

[Quickstart](#quickstart) · [Why Argus](#why-argus) · [The Committee](#the-committee) · [Architecture](#architecture) · [中文](#中文)

</div>

```
NVDA · $1,118.20 · +0.34%

┌─ Technical Analyst ──────────────── conviction 4/5 · bullish
│  RSI(14)=72 overbought, but golden cross intact since Nov;
│  MACD histogram flattening — short-term caution.
├─ Fundamental Analyst ────────────── conviction 3/5 · neutral
│  Fwd P/E 33 vs 5y avg 28 is rich; data-centre mix expanding,
│  earnings revisions still positive. 56% margin unprecedented.
├─ Sentiment Analyst ──────────────── conviction 4/5 · bullish
│  News flow re-affirms AI capex cycle; semis ETF inflows
│  sustained; narrative crowdedness rising.
├─ Macro Strategist ───────────────── conviction 4/5 · tailwind
│  Hyperscaler 2025 capex guidance keeps NVDA central.
│  Risks: export controls, sovereign capex pullback.
├─ Risk Manager ───────────────────── risk score 3/5
│  ATR(14)=$42 → 1×ATR stop ~$1,076; sizing 1.5–2.5% of book;
│  beta 1.7 means de-rate risk in a market drawdown.
├─ Flow Analyst ──────────────────── conviction 4/5 · accumulating
│  Form 4: 3 insider buys, 0 sells in 30d (CFO + 2 directors,
│  ~$4.2M net). Short interest 1.8% of float, DTC 1.2 — low
│  squeeze risk. Smart money quietly accumulating.
└─ Chief Investment Officer ─────────────────────────────────
   ACCUMULATE  ·  conviction 4/5  ·  horizon 3-6M
   Trend intact and macro setup structurally supportive, but
   technical extension argues for staged entry.
   Entry $1,070-1,095   Stop below $1,030
   Risks: hyperscaler capex pause · export-control escalation
          · AI-narrative crowdedness
```

<sub>Representative output. Argus generates this live, token-by-token, in the browser.</sub>

---

## Why Argus

Most retail stock tools answer *"what's this stock worth?"* with one signal — a P/E ratio, an RSI reading, an analyst rating.

Argus answers it **the way a real desk does: by debate.**

You give it a ticker. Six LLM agents — each playing a distinct role on a buy-side desk — read independent slices of the data, write their independent takes, and **disagree on purpose**. A Chief Investment Officer agent then resolves the conflict and produces a single recommendation with conviction, horizon, entry zone, and stop zone.

The whole deliberation streams to your screen, token by token. It looks the way fintech *should* look.

|                              | Argus                                              | Yahoo / TradingView | A single ChatGPT prompt    |
| ---------------------------- | -------------------------------------------------- | ------------------- | -------------------------- |
| **Multi-perspective analysis** | 6 specialised analysts + CIO synthesis             | One blended view    | One blended view           |
| **Smart-money flow signals** | Insider trades · short interest (US) · Northbound flow · Dragon-Tiger list (A-share) — read by a dedicated Flow Analyst agent | Not exposed | Not surfaced |
| **Markets**                  | US · A-share · HK in one workstation               | Per-market silos    | Whatever it can web-search |
| **Live streaming reasoning** | Token-by-token SSE; you can read agents *thinking* | n/a                 | Single block of text       |
| **Pluggable data**           | yfinance + akshare free; Finnhub / Tushare / Longbridge optional | Locked-in vendor    | None                       |
| **Pluggable LLM**            | Anthropic · OpenAI · DeepSeek · Qwen · **NVIDIA NIM** · Ollama | n/a                 | Locked to one              |
| **Self-hosted, open source** | MIT, runs on your laptop                           | Cloud SaaS          | Cloud SaaS                 |

## The Committee

Each ticker is read by a panel of LLM personas, then synthesised:

| Agent                       | Role                                                                                |
| --------------------------- | ----------------------------------------------------------------------------------- |
| **Technical Analyst**       | RSI, MACD, Bollinger, KDJ, ATR, OBV — cites specific readings                       |
| **Fundamental Analyst**     | P/E · P/B · P/S · growth · margin · moat vs sector                                  |
| **Sentiment Analyst**       | News headlines, narrative shifts, crowdedness                                       |
| **Macro Strategist**        | Sector + macro regime (rates, FX, AI capex, China demand, geopolitics)              |
| **Risk Manager**            | Volatility, beta, drawdown risk, position sizing, stop zone                         |
| **Flow Analyst**            | Insider transactions · short interest (US) · Northbound flow · Dragon-Tiger list (A-share) — what *smart money* is doing |
| **Chief Investment Officer** | Resolves disagreements → action · conviction · horizon · entry · stop · key risks  |

## Three markets, one workstation

| Market               | Coverage                                  | Data source (default)        | Search example                |
| -------------------- | ----------------------------------------- | ---------------------------- | ----------------------------- |
| US                   | NYSE · NASDAQ                              | yfinance                     | `AAPL`, `Apple`               |
| China A-shares        | Shanghai · Shenzhen · STAR · ChiNext      | akshare                      | `600519`, `茅台`              |
| Hong Kong            | HKEX                                       | yfinance + akshare           | `0700.HK`, `Tencent`, `腾讯`  |

The same Stock page, the same indicators, the same committee — across all three.

## Bring your own LLM

The first configured key wins, in priority order. UI-stored keys override `.env`.

| Provider                  | Default model                       | Notes                                  |
| ------------------------- | ----------------------------------- | -------------------------------------- |
| **Anthropic**             | `claude-opus-4-7`                   | Best agent reasoning quality           |
| **OpenAI**                | `gpt-5.5`                           | Latest flagship                        |
| **DeepSeek**              | `deepseek-v4-pro`                   | Strong, cost-effective                 |
| **Qwen** (DashScope)      | `qwen-plus`                         | Good for Chinese-market commentary     |
| **NVIDIA NIM**            | `minimaxai/minimax-m2.7`            | Free tier on `build.nvidia.com`        |
| **Ollama** (local)        | `llama3.1`                          | 100% offline, BYO model                |

Open Settings → paste a key → it works immediately. No restart.

## Quickstart

**Prerequisites:** Python 3.11+, Node 20+. An LLM key is optional — Argus runs in demo mode without one.

```bash
git clone https://github.com/auronsun/argus.git
cd argus
cp .env.example .env                                                    # optional: paste keys

# Backend  →  http://127.0.0.1:8765
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn argus.main:app --reload --host 127.0.0.1 --port 8765

# Frontend →  http://127.0.0.1:5173
cd ../frontend && npm install && npm run dev
```

Open the UI, type `AAPL`, `600519`, or `0700.HK` in the search bar, click **Run** on the AI Committee panel, and watch the desk argue.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          React + Vite UI                         │
│   Dashboard │ Stock Deep-Dive │ Screener │ Watchlist │ Settings  │
└────────────────────────┬─────────────────────────────────────────┘
                         │  REST + SSE + WebSocket
┌────────────────────────┴─────────────────────────────────────────┐
│                      FastAPI · Python 3.11                       │
│ ┌──────────────┐  ┌────────────────┐  ┌──────────────────────┐   │
│ │  Market      │  │  Analysis      │  │  Multi-Agent         │   │
│ │  Adapters    │  │  Engine        │  │  Committee           │   │
│ │ (US/CN/HK)   │  │ (indicators,   │  │ (5 analysts + CIO,   │   │
│ │  TTL cached  │  │  fundamentals) │  │  streamed reasoning) │   │
│ └──────────────┘  └────────────────┘  └──────────────────────┘   │
│        SQLite (state) + Parquet cache (OHLCV)                    │
└──────────────────────────────────────────────────────────────────┘
```

Long form: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Sharing & export

Designed for showing your work, not for spam.

- **Stock page** → *Copy summary* (Markdown) · *Copy link*
- **Verdict card** → *Export Markdown* (one file with action / thesis / risks / entry / stop / disclaimer)
- **Watchlist** → *Export JSON* / *Import JSON* — share starter watchlists with friends

Every exported artefact carries the disclaimer below. Nothing leaks API keys, paths, or local config.

## Scope & limitations

Argus is **a single-user research tool that runs on your laptop**, not a multi-tenant
SaaS. A few things worth knowing up-front, in honest terms:

- **No authentication.** The local HTTP API trusts whoever can reach the port.
  Don't bind it to a public IP. See [SECURITY.md](SECURITY.md).
- **Free data has limits.** yfinance and akshare are best-effort public endpoints
  — they rate-limit, occasionally rename columns, and can return empty for
  thinly-covered tickers. Argus mitigates with TTL caching and a Finnhub fallback
  for news; for serious use, plug in a paid feed (Tushare Pro, Finnhub real-time,
  Longbridge).
- **"Real-time" means 5-second polling.** Argus polls the underlying adapters; it
  is not wired to vendor-native streaming. Quotes can lag a few seconds.
- **Free-tier LLM streams sometimes drop.** NVIDIA NIM free tier in particular
  closes long streams mid-flight; the CIO call retries once on transport failures,
  and analyst cards display an explicit notice if a model returned no content.
- **What's wired today** in the Flow Analyst: insider transactions + short interest
  for US tickers; Northbound (Stock Connect) flow + Dragon-Tiger list for A-shares.
  HK flow signals and 融资余额 are placeholders pending future work — when you analyse
  those tickers the Flow Analyst will say so explicitly rather than fabricate numbers.

If you want to run Argus somewhere other than localhost, treat that as a
project rather than a config flip — the [SECURITY.md](SECURITY.md) hardening
checklist is a starting point.

## Acknowledgements

Argus stands on the shoulders of [yfinance](https://github.com/ranaroussi/yfinance), [akshare](https://github.com/akfamily/akshare), [FastAPI](https://fastapi.tiangolo.com/), [Recharts](https://recharts.org/), and [TradingView Lightweight Charts](https://tradingview.github.io/lightweight-charts/).

## License

[MIT](LICENSE).

> **Argus is research and education software. Nothing it produces is investment advice.**
> Past performance does not predict future results. Always do your own due diligence.

---

<a id="中文"></a>

## 中文

### 用一百只眼睛盯每一个市场。

**Argus** 是一个开源 **AI 投资委员会**，覆盖 美股 · A 股 · 港股。
六位分工不同的 LLM 分析师（含**业内独有的资金流分析师**：读懂内幕交易、空头持仓（美股）、北向资金、龙虎榜（A 股））+ 一位首席投资官（CIO）实时辩论一只股票，并给出最终判断——
全程 token 级流式呈现，UI 是质感不输付费产品的玻璃拟态界面。

### 为什么是 Argus

零售股票工具回答"这只股票怎么样"通常只给一个信号——一个 P/E、一个 RSI、一个评级。

Argus 用真实交易台的方式回答：**让分析师们辩论**。

你输入一只代码，六位 LLM 分析师各自读取不同的数据切片，独立得出观点，**故意会有分歧**。CIO Agent 综合所有观点，给出带置信度、持有期、入场区间、止损区间的最终建议。

整个推理过程逐字流式显示。这才是 fintech 应该有的样子。

### 一分钟启动

```bash
git clone https://github.com/auronsun/argus.git && cd argus
cp .env.example .env
cd backend && pip install -r requirements.txt && uvicorn argus.main:app --reload --host 127.0.0.1 --port 8765 &
cd ../frontend && npm install && npm run dev
```

打开 `http://127.0.0.1:5173`，搜 `茅台` / `腾讯` / `NVDA`——委员会立刻开始辩论。

### 委员会成员

| 角色            | 关注                                                                          |
| --------------- | ----------------------------------------------------------------------------- |
| 技术分析师      | RSI · MACD · BOLL · KDJ · ATR · OBV——引用具体读数                              |
| 基本面分析师    | PE · PB · PS · 增长 · 利润率 · 护城河 vs 行业                                 |
| 情绪分析师      | 新闻头条 · 叙事变化 · 拥挤度                                                  |
| 宏观策略师      | 行业 + 宏观周期（利率 / 汇率 / AI 资本开支 / 中国需求 / 地缘）                |
| 风险经理        | 波动率 · Beta · 回撤风险 · 仓位区间 · 止损                                    |
| 资金流分析师    | 内幕交易 · 空头持仓（美股）· 北向资金 · 龙虎榜（A 股）——读懂"聪明钱"在做什么     |
| 首席投资官（CIO） | 综合所有观点 → 操作 · 置信度 · 持有期 · 入场区间 · 止损 · 主要风险            |

### 自由切换 LLM 与数据源

- **LLM**：Anthropic · OpenAI · DeepSeek · 通义千问 · **NVIDIA NIM** · Ollama（本地）
- **行情**：免费源 yfinance / akshare 开箱即用；Finnhub · Alpha Vantage · Tushare Pro · Longbridge 填 Key 即可启用
- 在「设置」页粘贴 Key，**无需重启**——立即生效

### 免责声明

> 本软件仅供研究与教育用途。任何输出**不构成投资建议**，过往业绩不预示未来表现，请独立做尽职调查。

