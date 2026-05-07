import clsx, { type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmt(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  if (Math.abs(n) >= 1_000_000_000_000) return (n / 1_000_000_000_000).toFixed(2) + "T";
  if (Math.abs(n) >= 1_000_000_000) return (n / 1_000_000_000).toFixed(2) + "B";
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(2) + "M";
  if (Math.abs(n) >= 1_000) return n.toLocaleString(undefined, { maximumFractionDigits: digits });
  return n.toFixed(digits);
}

export function fmtPct(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
}

export function changeClass(n: number | null | undefined): string {
  if (!n) return "text-zinc-300";
  return n > 0 ? "text-bull" : "text-bear";
}

export function marketLabel(m: string): { code: string; label: string; cls: string } {
  switch (m) {
    case "US": return { code: "US", label: "US",      cls: "text-sky-300 ring-sky-400/30 bg-sky-500/10" };
    case "CN": return { code: "CN", label: "A-Share", cls: "text-rose-300 ring-rose-400/30 bg-rose-500/10" };
    case "HK": return { code: "HK", label: "HK",      cls: "text-amber-300 ring-amber-400/30 bg-amber-500/10" };
    default:   return { code: m,    label: m,         cls: "text-zinc-300 ring-white/15 bg-white/5" };
  }
}
