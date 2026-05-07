/**
 * Committee run store — owns the SSE connection and the streaming state for
 * each in-flight or completed analysis, keyed by `${symbol}::${lang}`.
 *
 * Why a module-level singleton instead of component state:
 *
 * The committee makes 5+1 sequential LLM calls and a full run takes 30-90s
 * end-to-end. If state lives in the component, navigating away unmounts the
 * panel, kills the EventSource via cleanup, and discards everything streamed
 * so far. Most users never get to a verdict. This store outlives the
 * component lifecycle so that:
 *   - You can start a run, navigate away, come back, and see it still
 *     running (or completed).
 *   - You can run committees on multiple symbols in parallel; each is
 *     independent.
 *
 * Lifetime: in-memory only, survives within a session. A page refresh /
 * tab close drops everything. (localStorage persistence would add cross-tab
 * survival but is overkill for v1.)
 */
import { streamCommittee, streamRetryAgent, type CommitteeEvent } from "@/api/client";
import { addHistory } from "./history";

export type AgentStatus = "idle" | "thinking" | "done" | "error";

export interface AgentState {
  role: string;
  status: AgentStatus;
  text: string;
}

export interface Verdict {
  action?: string;
  conviction?: number;
  horizon?: string;
  thesis?: string;
  key_risks?: string[];
  entry_zone?: string;
  stop_zone?: string;
  raw?: string;
}

export interface RunState {
  symbol: string;
  lang: "en" | "zh";
  agents: Record<string, AgentState>;
  verdict: Verdict | null;
  running: boolean;
  startedAt: number;
  completedAt: number | null;
  error?: string;
}

const ROLES = ["technical", "fundamental", "sentiment", "macro", "risk", "flow"] as const;

export function initAgents(): Record<string, AgentState> {
  const out: Record<string, AgentState> = {};
  [...ROLES, "cio"].forEach((r) => (out[r] = { role: r, status: "idle", text: "" }));
  return out;
}

type Listener = (state: RunState | null) => void;

class CommitteeStore {
  private runs = new Map<string, RunState>();
  private closers = new Map<string, () => void>();
  private listeners = new Map<string, Set<Listener>>();

  private k(symbol: string, lang: string): string {
    return `${symbol}::${lang}`;
  }

  get(symbol: string, lang: "en" | "zh"): RunState | null {
    return this.runs.get(this.k(symbol, lang)) ?? null;
  }

  subscribe(symbol: string, lang: "en" | "zh", listener: Listener): () => void {
    const key = this.k(symbol, lang);
    let set = this.listeners.get(key);
    if (!set) {
      set = new Set();
      this.listeners.set(key, set);
    }
    set.add(listener);
    listener(this.runs.get(key) ?? null);
    return () => {
      set!.delete(listener);
    };
  }

  private emit(key: string): void {
    const state = this.runs.get(key) ?? null;
    this.listeners.get(key)?.forEach((l) => l(state));
  }

  start(symbol: string, lang: "en" | "zh"): void {
    const key = this.k(symbol, lang);
    const existing = this.runs.get(key);
    if (existing?.running) return; // already in flight — nothing to do

    const state: RunState = {
      symbol,
      lang,
      agents: initAgents(),
      verdict: null,
      running: true,
      startedAt: Date.now(),
      completedAt: null,
    };
    this.runs.set(key, state);
    this.emit(key);

    const closer = streamCommittee(symbol, (ev) => this.handleEvent(key, ev), { lang });
    this.closers.set(key, closer);
  }

  /** User-initiated reset — kills the connection and forgets results. */
  reset(symbol: string, lang: "en" | "zh"): void {
    const key = this.k(symbol, lang);
    this.closers.get(key)?.();
    this.closers.delete(key);
    this.runs.delete(key);
    this.emit(key);
  }

  /** Re-run a single analyst (or the CIO) without wasting calls on the
   * five other analysts. We pass their previously-captured texts to the
   * backend so the CIO can resynthesise. */
  retryAgent(
    symbol: string,
    lang: "en" | "zh",
    role: "technical" | "fundamental" | "sentiment" | "macro" | "risk" | "flow" | "cio",
  ): void {
    const key = this.k(symbol, lang);
    const state = this.runs.get(key);
    if (!state || state.running) return;

    // Collect existing analyst texts EXCEPT the role we're retrying.
    // (CIO is rerun on every retry; its prior text is meaningless.)
    const existing: Record<string, string> = {};
    for (const r of ROLES) {
      if (r === role) continue;
      const txt = state.agents[r]?.text ?? "";
      if (txt.trim()) existing[r] = txt;
    }

    // Optimistic UI: clear the agent we're about to rerun + mark CIO as
    // queued again (it will rerun after the analyst is done).
    if (role !== "cio") {
      state.agents[role] = { role, status: "thinking", text: "" };
    }
    state.agents.cio = { role: "cio", status: "idle", text: "" };
    state.verdict = null;
    state.running = true;
    state.completedAt = null;
    this.emit(key);

    const closer = streamRetryAgent(
      symbol, { role, lang, existing_outputs: existing },
      (ev) => this.handleEvent(key, ev),
    );
    this.closers.set(key, closer);
  }

  private handleEvent(key: string, ev: CommitteeEvent): void {
    const state = this.runs.get(key);
    if (!state) return;

    if (ev.type === "verdict") {
      state.verdict = ev.payload as Verdict;
    } else if (ev.type === "done") {
      state.running = false;
      state.completedAt = Date.now();
      this.closers.delete(key);
      // Once a run finishes with a verdict, persist a small entry to
      // localStorage so the user can browse "recent analyses" even after
      // the in-memory store is gone (page refresh / new session).
      if (state.verdict) {
        addHistory({
          symbol: state.symbol,
          lang: state.lang,
          verdict: state.verdict,
          completedAt: state.completedAt,
        });
      }
    } else if (ev.role) {
      const a = state.agents[ev.role];
      if (a) {
        if (ev.type === "agent_start") {
          a.status = "thinking";
          a.text = "";
        } else if (ev.type === "agent_token") {
          a.text += ev.text;
        } else if (ev.type === "agent_done") {
          a.status = "done";
        } else if (ev.type === "error") {
          a.status = "error";
          a.text = ev.text;
        }
      }
    } else if (ev.type === "error") {
      state.error = ev.text;
      state.running = false;
      state.completedAt = Date.now();
      this.closers.delete(key);
    }
    this.emit(key);
  }
}

export const committeeStore = new CommitteeStore();
