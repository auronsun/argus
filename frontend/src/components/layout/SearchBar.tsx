import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { api, type SearchResult } from "@/api/client";
import { cn, marketLabel } from "@/lib/cn";
import { useT } from "@/lib/i18n";
import { MarketBadge } from "@/components/ui/MarketBadge";

export function SearchBar({ size = "md" }: { size?: "md" | "lg" }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const t = useT();

  useEffect(() => {
    if (q.trim().length < 1) {
      setResults([]);
      return;
    }
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const r = await api.search(q.trim());
        setResults(r.results);
        setOpen(true);
        setActive(0);
      } finally {
        setLoading(false);
      }
    }, 200);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, []);

  function go(r?: SearchResult) {
    const target = r ?? results[active];
    if (target) {
      navigate(`/stock/${encodeURIComponent(target.symbol)}`);
      setOpen(false);
      setQ("");
    } else if (q.trim()) {
      navigate(`/stock/${encodeURIComponent(q.trim().toUpperCase())}`);
      setOpen(false);
      setQ("");
    }
  }

  const heightCls = size === "lg" ? "h-14 text-base" : "h-11 text-sm";

  return (
    <div className="relative w-full" ref={ref}>
      <div className={cn("gradient-border rounded-xl", "transition-all")}>
        <div className={cn("flex items-center gap-3 px-4 rounded-xl glass-strong", heightCls)}>
          <Search className="w-4 h-4 text-zinc-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onFocus={() => results.length && setOpen(true)}
            onKeyDown={(e) => {
              if (e.key === "Enter") go();
              if (e.key === "ArrowDown") setActive((a) => Math.min(a + 1, results.length - 1));
              if (e.key === "ArrowUp") setActive((a) => Math.max(a - 1, 0));
              if (e.key === "Escape") setOpen(false);
            }}
            placeholder={t("search.placeholder")}
            className="flex-1 bg-transparent outline-none placeholder:text-zinc-500 text-zinc-100"
          />
          {loading && <span className="text-xs text-zinc-500">…</span>}
          <kbd className="hidden md:inline-flex text-[10px] px-1.5 py-0.5 rounded border border-white/10 text-zinc-400 font-mono">↵</kbd>
        </div>
      </div>

      {open && results.length > 0 && (
        <div className="absolute z-50 left-0 right-0 mt-2 glass rounded-xl overflow-hidden border border-white/10 max-h-96 overflow-y-auto">
          {results.map((r, i) => {
            const m = marketLabel(r.market);
            return (
              <button
                key={r.symbol}
                onMouseEnter={() => setActive(i)}
                onClick={() => go(r)}
                className={cn(
                  "w-full px-4 py-3 flex items-center gap-3 text-left transition-colors",
                  i === active ? "bg-white/5" : "hover:bg-white/[0.03]"
                )}
              >
                <MarketBadge market={r.market} />
                <div className="flex-1 min-w-0">
                  <div className="font-mono text-sm text-zinc-100">{r.symbol}</div>
                  <div className="text-xs text-zinc-400 truncate">{r.name}</div>
                </div>
                <span className="text-[10px] text-zinc-500">{r.exchange ?? m.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
