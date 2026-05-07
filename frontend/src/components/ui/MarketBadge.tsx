import { cn, marketLabel } from "@/lib/cn";

export function MarketBadge({ market, size = "sm" }: { market: string; size?: "sm" | "md" }) {
  const m = marketLabel(market);
  const sizeCls = size === "md" ? "h-7 px-2 text-[11px]" : "h-5 px-1.5 text-[10px]";
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-md font-mono font-medium uppercase ring-1 tracking-wider",
        sizeCls,
        m.cls
      )}
    >
      {m.code}
    </span>
  );
}
