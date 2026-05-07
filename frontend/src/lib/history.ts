/**
 * Analysis history — a small localStorage log of completed committee runs.
 *
 * Each entry is the minimum needed to render a "Recent analyses" list and
 * link back to the underlying committee run (which itself lives in
 * committeeStore for the current session). Cross-session history is best
 * effort: the verdict snapshot is preserved here even after committeeStore
 * is gone (page refresh).
 *
 * v1: client-side only. A future backend table can subscribe to the same
 * shape if we want cross-device history.
 */

import type { Verdict } from "./committee-store";

const STORAGE_KEY = "argus.history.v1";
const MAX_ENTRIES = 50;

export interface HistoryEntry {
  symbol: string;
  market?: string;       // best-effort, may be unknown when first persisted
  name?: string;
  lang: "en" | "zh";
  verdict: Verdict;
  completedAt: number;   // epoch ms
}

type Listener = (entries: HistoryEntry[]) => void;
const listeners = new Set<Listener>();

function read(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write(entries: HistoryEntry[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, MAX_ENTRIES)));
  } catch {
    /* storage full / disabled — silently ignore */
  }
  for (const l of listeners) l(read());
}

export function listHistory(): HistoryEntry[] {
  return read().sort((a, b) => b.completedAt - a.completedAt);
}

export function addHistory(entry: HistoryEntry): void {
  const all = read();
  // De-dup: drop any earlier run on the same (symbol, lang) — we keep only
  // the latest because it makes the list more useful and saves space.
  const filtered = all.filter(
    (e) => !(e.symbol === entry.symbol && e.lang === entry.lang)
  );
  filtered.unshift(entry);
  write(filtered);
}

export function removeHistory(symbol: string, lang: "en" | "zh"): void {
  write(read().filter((e) => !(e.symbol === symbol && e.lang === lang)));
}

export function clearHistory(): void {
  write([]);
}

export function subscribeHistory(listener: Listener): () => void {
  listeners.add(listener);
  listener(listHistory());
  return () => listeners.delete(listener);
}
