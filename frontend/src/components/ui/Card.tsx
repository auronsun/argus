import { type ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Card({ children, className, glow }: { children: ReactNode; className?: string; glow?: boolean }) {
  return (
    <div
      className={cn(
        "glass rounded-2xl p-5 relative overflow-hidden",
        glow && "shadow-[0_0_60px_-30px_rgba(124,58,237,0.6)]",
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, right }: { title: ReactNode; subtitle?: ReactNode; right?: ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-3">
      <div>
        <div className="text-xs uppercase tracking-[0.18em] text-zinc-400">{title}</div>
        {subtitle && <div className="text-zinc-200 mt-1 text-sm">{subtitle}</div>}
      </div>
      {right}
    </div>
  );
}
