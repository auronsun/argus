const BASE = "";

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail || `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
  /** Best-effort i18n bucket: 'upstream' for 5xx, 'validation' for 4xx, 'network' for 0. */
  get kind(): "network" | "validation" | "upstream" | "unknown" {
    if (this.status === 0) return "network";
    if (this.status >= 500) return "upstream";
    if (this.status >= 400) return "validation";
    return "unknown";
  }
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, init);
  } catch (e: any) {
    throw new ApiError(0, e?.message || "network error");
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body?.detail)) {
        // pydantic 422 — surface the first message
        detail = body.detail.map((d: any) => d?.msg ?? JSON.stringify(d)).join("; ");
      }
    } catch {
      /* non-JSON body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

export type Market = "US" | "CN" | "HK";

export interface Quote {
  symbol: string; market: Market; name: string;
  price: number; change: number; change_pct: number;
  open: number | null; high: number | null; low: number | null;
  prev_close: number | null; volume: number | null; market_cap: number | null;
  currency: string; timestamp: string;
}

export interface Candle { time: string; open: number; high: number; low: number; close: number; volume: number; }

export interface Fundamentals {
  symbol: string; market: Market; name: string; sector: string | null; industry: string | null;
  market_cap: number | null; currency: string;
  pe_ratio: number | null; forward_pe: number | null; pb_ratio: number | null; ps_ratio: number | null;
  dividend_yield: number | null; eps: number | null; revenue_ttm: number | null; profit_margin: number | null;
  beta: number | null; fifty_two_week_high: number | null; fifty_two_week_low: number | null;
  summary: string | null;
}

export interface SearchResult { symbol: string; name: string; market: Market; exchange: string | null; }

export interface Capabilities {
  version: string;
  llm: { configured: boolean; provider: string | null; model: string | null;
         available: Record<string, boolean>; };
  data: Record<string, boolean>;
  markets: string[];
}

export interface KeyEntry {
  configured: boolean;
  source: "ui" | "env" | null;
  /** present only for LLM provider entries */
  model?: string;
  model_source?: "ui" | "env" | null;
}

export interface KeysStatus {
  active_llm: { provider: string; model: string } | null;
  providers: Record<string, KeyEntry>;
}

export type SmokeKind =
  | "ok"
  | "no_key"
  | "auth"
  | "model_not_found"
  | "rate_limit"
  | "network"
  | "timeout"
  | "unknown";

export interface SmokeTestResult {
  ok: boolean;
  kind: SmokeKind;
  detail?: string;
  latency_ms?: number;
  model?: string;
  provider?: string;
  sample?: string;
}

export const api = {
  capabilities: () => http<Capabilities>("/api/system/capabilities"),
  keysGet: () => http<KeysStatus>("/api/settings/keys"),
  keysUpdate: (updates: Record<string, string>) =>
    http<KeysStatus>(`/api/settings/keys`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ updates }),
    }),
  keysClear: (slot: string) => http<KeysStatus>(`/api/settings/keys/${slot}`, { method: "DELETE" }),
  keysTest:  (slot: string) => http<SmokeTestResult>(`/api/settings/test/${slot}`, { method: "POST" }),
  search: (q: string) => http<{ results: SearchResult[] }>(`/api/market/search?q=${encodeURIComponent(q)}`),
  quote: (symbol: string) => http<Quote>(`/api/market/quote/${encodeURIComponent(symbol)}`),
  history: (symbol: string, interval = "1d") =>
    http<{ candles: Candle[]; interval: string }>(`/api/market/history/${encodeURIComponent(symbol)}?interval=${interval}`),
  indicators: (symbol: string, interval = "1d") =>
    http<{ indicators: { series: any[]; latest: any }; signals: Record<string, string> }>(
      `/api/analysis/indicators/${encodeURIComponent(symbol)}?interval=${interval}`),
  fundamentals: (symbol: string) => http<Fundamentals>(`/api/analysis/fundamentals/${encodeURIComponent(symbol)}`),
  news: (symbol: string, limit = 8) =>
    http<{ items: { title: string; publisher: string | null; url: string | null; published: any; summary: string }[] }>(
      `/api/market/news/${encodeURIComponent(symbol)}?limit=${limit}`),
  screenerPreset: (name: string) => http<{ rows: any[] }>(`/api/screener/preset/${name}`),
  screenerRun: (criteria: any) =>
    http<{ rows: any[] }>(`/api/screener/run`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(criteria),
    }),
  watchlist: () => http<{ items: any[] }>("/api/watchlist"),
  watchAdd: (symbol: string, note = "") =>
    http(`/api/watchlist`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ symbol, note }),
    }),
  watchRemove: (id: number) => http(`/api/watchlist/${id}`, { method: "DELETE" }),
  alerts: () => http<{ alerts: any[] }>("/api/watchlist/alerts"),
  alertAdd: (a: { symbol: string; metric: string; op: string; threshold: number; note?: string }) =>
    http(`/api/watchlist/alerts`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(a),
    }),
  alertRemove: (id: number) => http(`/api/watchlist/alerts/${id}`, { method: "DELETE" }),
  alertEvaluate: () => http<{ triggered: any[] }>("/api/watchlist/alerts/evaluate", { method: "POST" }),
};

export interface CommitteeEvent {
  type: "agent_start" | "agent_token" | "agent_done" | "verdict" | "error" | "done";
  role: "technical" | "fundamental" | "sentiment" | "macro" | "risk" | "cio" | null;
  agent_name: string;
  text: string;
  payload: Record<string, any>;
}

export function streamCommittee(
  symbol: string,
  onEvent: (ev: CommitteeEvent) => void,
  opts: { lang?: "en" | "zh" } = {}
): () => void {
  const lang = opts.lang ?? "en";
  const url = `/api/committee/stream/${encodeURIComponent(symbol)}?lang=${lang}`;
  const es = new EventSource(url);
  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent(data as CommitteeEvent);
      if (data.type === "done") es.close();
    } catch {
      /* ignore malformed */
    }
  };
  es.onerror = () => es.close();
  return () => es.close();
}
