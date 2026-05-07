import { type ReactNode } from "react";
import { cn } from "@/lib/cn";

type Tone = "default" | "bull" | "bear" | "warn" | "info";

export function Badge({ children, tone = "default", className }: { children: ReactNode; tone?: Tone; className?: string }) {
  const styles: Record<Tone, string> = {
    default: "bg-white/5 text-zinc-300 border-white/10",
    bull: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    bear: "bg-rose-500/10 text-rose-300 border-rose-500/30",
    warn: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    info: "bg-cyan-500/10 text-cyan-300 border-cyan-500/30",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[11px] font-medium uppercase tracking-wider",
        styles[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
