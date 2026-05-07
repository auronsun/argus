import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Sparkles, TrendingUp, Filter, Star } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { MarketBadge } from "@/components/ui/MarketBadge";
import { SearchBar } from "@/components/layout/SearchBar";
import { changeClass, fmt, fmtPct } from "@/lib/cn";
import { useT } from "@/lib/i18n";

const FEATURED = ["AAPL", "NVDA", "TSLA", "600519.SH", "0700.HK", "9988.HK"];

export function Dashboard() {
  const t = useT();
  const { data: caps } = useQuery({ queryKey: ["caps"], queryFn: api.capabilities });

  return (
    <div className="relative">
      {/* Hero */}
      <section className="relative px-8 pt-12 pb-8 overflow-hidden">
        <div className="absolute inset-0 mesh-bg opacity-60 pointer-events-none" />
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative max-w-4xl"
        >
          <div className="flex items-center gap-2 mb-4">
            <Badge tone="info"><Sparkles className="w-3 h-3 mr-1" /> {t("dashboard.badge")}</Badge>
            <Badge>{t("dashboard.alpha")}</Badge>
          </div>
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight bg-gradient-to-br from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            {t("dashboard.heroLine1")}<br />
            {t("dashboard.heroLine2")}{" "}
            <span className="bg-gradient-to-r from-violet-400 via-cyan-300 to-pink-400 bg-clip-text">
              {t("dashboard.heroBrand")}
            </span>
          </h1>
          <p className="text-zinc-400 mt-4 max-w-2xl text-base leading-relaxed">{t("dashboard.heroDesc")}</p>
          <div className="mt-7 max-w-2xl">
            <SearchBar size="lg" />
          </div>
          <div className="mt-3 text-xs text-zinc-500 flex flex-wrap gap-x-4 gap-y-1">
            {t("dashboard.try")}
            {FEATURED.map((s) => (
              <Link key={s} to={`/stock/${encodeURIComponent(s)}`} className="text-cyan-400 hover:underline font-mono">
                {s}
              </Link>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Quick links */}
      <section className="px-8 pb-12 grid md:grid-cols-3 gap-4">
        <QuickCard
          to="/stock/AAPL" icon={<TrendingUp className="w-4 h-4" />} title={t("dashboard.cardDeep.title")}
          tag={t("dashboard.cardDeep.tag")} desc={t("dashboard.cardDeep.desc")}
        />
        <QuickCard
          to="/screener" icon={<Filter className="w-4 h-4" />} title={t("dashboard.cardScreener.title")}
          tag={t("dashboard.cardScreener.tag")} desc={t("dashboard.cardScreener.desc")}
        />
        <QuickCard
          to="/watchlist" icon={<Star className="w-4 h-4" />} title={t("dashboard.cardWatch.title")}
          tag={t("dashboard.cardWatch.tag")} desc={t("dashboard.cardWatch.desc")}
        />
      </section>

      {/* Featured tickers preview */}
      <section className="px-8 pb-16">
        <div className="text-xs uppercase tracking-[0.2em] text-zinc-500 mb-3">{t("dashboard.snapshot")}</div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {FEATURED.map((sym) => <TickerTile key={sym} symbol={sym} />)}
        </div>
      </section>

      {/* Footer note */}
      <div className="px-8 pb-10 text-xs max-w-3xl">
        {caps && !caps.llm.configured && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-amber-200">
            {t("dashboard.demoNotice")}
          </div>
        )}
      </div>
    </div>
  );
}

function QuickCard({ to, icon, title, tag, desc }: { to: string; icon: React.ReactNode; title: string; tag: string; desc: string }) {
  return (
    <Link to={to} className="group">
      <Card className="h-full transition-transform group-hover:-translate-y-0.5 group-hover:bg-white/[0.06]">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-violet-500/30 to-cyan-500/30 grid place-items-center text-zinc-100">
            {icon}
          </div>
          <div>
            <div className="font-medium">{title}</div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">{tag}</div>
          </div>
        </div>
        <div className="text-sm text-zinc-400">{desc}</div>
      </Card>
    </Link>
  );
}

function TickerTile({ symbol }: { symbol: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["quote", symbol],
    queryFn: () => api.quote(symbol),
    refetchInterval: 30_000,
  });
  return (
    <Link to={`/stock/${encodeURIComponent(symbol)}`} className="group">
      <Card className="!p-4 hover:bg-white/[0.06] transition-colors h-full">
        <div className="flex items-start justify-between">
          <div className="min-w-0">
            <div className="font-mono text-sm text-zinc-100">{symbol}</div>
            <div className="text-[10px] text-zinc-500 truncate">{data?.name ?? "—"}</div>
          </div>
          {data && <MarketBadge market={data.market} />}
        </div>
        <div className="mt-2 flex items-baseline justify-between">
          <div className="text-xl font-semibold tabular-nums num-fade-in">
            {isLoading ? "…" : fmt(data?.price)}
          </div>
          <div className={`text-xs font-medium ${changeClass(data?.change_pct)}`}>
            {fmtPct(data?.change_pct)}
          </div>
        </div>
      </Card>
    </Link>
  );
}
