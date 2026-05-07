import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { api } from "@/api/client";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { MarketBadge } from "@/components/ui/MarketBadge";
import { ErrorState } from "@/components/ui/ErrorState";
import { ShareSummary } from "@/components/share/ShareSummary";
import { PriceChart } from "@/components/charts/PriceChart";
import { RSIChart, MACDChart } from "@/components/charts/IndicatorChart";
import { CommitteePanel } from "@/components/committee/CommitteePanel";
import { changeClass, fmt, fmtPct } from "@/lib/cn";
import { useT } from "@/lib/i18n";
import { useState } from "react";

const INTERVALS = [
  { v: "1d", label: "1D" },
  { v: "1wk", label: "1W" },
  { v: "1mo", label: "1M" },
];

export function StockPage() {
  const { symbol = "AAPL" } = useParams();
  const [interval, setInterval] = useState<"1d" | "1wk" | "1mo">("1d");
  const t = useT();

  const quote = useQuery({ queryKey: ["quote", symbol], queryFn: () => api.quote(symbol), refetchInterval: 15_000 });
  const fund = useQuery({ queryKey: ["fund", symbol], queryFn: () => api.fundamentals(symbol) });
  const ind = useQuery({ queryKey: ["ind", symbol, interval], queryFn: () => api.indicators(symbol, interval) });
  const news = useQuery({ queryKey: ["news", symbol], queryFn: () => api.news(symbol) });

  const series = ind.data?.indicators.series ?? [];
  const candles = series.map((s: any) => ({
    time: s.time, open: s.open, high: s.high, low: s.low, close: s.close, volume: s.volume,
  }));

  const isUp = (quote.data?.change_pct ?? 0) >= 0;

  // Quote is the page's anchor data; if it fails, fall back to a recoverable error state.
  if (quote.isError) {
    return (
      <div className="px-6 py-6">
        <ErrorState error={quote.error} onRetry={() => quote.refetch()} />
      </div>
    );
  }

  return (
    <div className="px-6 py-6 space-y-6">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        {/* Header */}
        <Card className="!p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              {quote.data && <MarketBadge market={quote.data.market} size="md" />}
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-2xl font-mono">{quote.data?.symbol ?? symbol}</h1>
                  {fund.data?.sector && <Badge tone="info">{fund.data.sector}</Badge>}
                </div>
                <div className="text-zinc-300 text-sm mt-1">{quote.data?.name || fund.data?.name || "—"}</div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-4xl font-semibold tabular-nums num-fade-in">
                {quote.isLoading ? <Spinner /> : fmt(quote.data?.price)}
                <span className="text-sm ml-2 text-zinc-500">{quote.data?.currency}</span>
              </div>
              <div className={`flex items-center gap-1 justify-end text-sm font-medium ${changeClass(quote.data?.change_pct)}`}>
                {isUp ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                {fmt(quote.data?.change)} · {fmtPct(quote.data?.change_pct)}
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mt-5 text-xs">
            <Stat label={t("stat.open")} value={fmt(quote.data?.open)} />
            <Stat label={t("stat.high")} value={fmt(quote.data?.high)} />
            <Stat label={t("stat.low")} value={fmt(quote.data?.low)} />
            <Stat label={t("stat.prevClose")} value={fmt(quote.data?.prev_close)} />
            <Stat label={t("stat.volume")} value={fmt(quote.data?.volume, 0)} />
            <Stat label={t("stat.marketCap")} value={fmt(quote.data?.market_cap, 0)} />
          </div>
        </Card>
      </motion.div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Chart + indicators */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader
              title={t("stock.priceVolume")}
              right={
                <div className="flex gap-1">
                  {INTERVALS.map((iv) => (
                    <Button
                      key={iv.v}
                      variant={interval === iv.v ? "primary" : "subtle"}
                      onClick={() => setInterval(iv.v as any)}
                      className="!px-3 !py-1 text-xs"
                    >
                      {iv.label}
                    </Button>
                  ))}
                </div>
              }
            />
            {ind.isError ? (
              <ErrorState compact error={ind.error} onRetry={() => ind.refetch()} />
            ) : ind.isLoading ? (
              <div className="h-[380px] grid place-items-center"><Spinner /></div>
            ) : (
              <PriceChart candles={candles} />
            )}
          </Card>

          <div className="grid md:grid-cols-2 gap-4">
            <Card>
              <CardHeader title="RSI (14)" subtitle={ind.data?.signals?.rsi} />
              <RSIChart data={series} />
            </Card>
            <Card>
              <CardHeader title="MACD" subtitle={ind.data?.signals?.macd} />
              <MACDChart data={series} />
            </Card>
          </div>

          <Card>
            <CardHeader title={t("stock.signals")} />
            <div className="flex flex-wrap gap-2">
              {Object.entries(ind.data?.signals ?? {}).map(([k, v]) => (
                <Badge key={k} tone={signalTone(v)}>{k}: {v}</Badge>
              ))}
              {(!ind.data?.signals || Object.keys(ind.data.signals).length === 0) && (
                <span className="text-xs text-zinc-500">{t("stock.noSignals")}</span>
              )}
            </div>
          </Card>
        </div>

        {/* Fundamentals + news */}
        <div className="space-y-6">
          <Card>
            <CardHeader title={t("stock.fundamentals")} />
            <div className="grid grid-cols-2 gap-3 text-xs">
              <Stat label={t("stat.peTrailing")} value={fmt(fund.data?.pe_ratio)} />
              <Stat label={t("stat.peForward")} value={fmt(fund.data?.forward_pe)} />
              <Stat label={t("stat.pb")} value={fmt(fund.data?.pb_ratio)} />
              <Stat label={t("stat.ps")} value={fmt(fund.data?.ps_ratio)} />
              <Stat label={t("stat.divYield")} value={fund.data?.dividend_yield ? `${(fund.data.dividend_yield * 100).toFixed(2)}%` : "—"} />
              <Stat label={t("stat.epsTtm")} value={fmt(fund.data?.eps)} />
              <Stat label={t("stat.profitMargin")} value={fund.data?.profit_margin ? `${(fund.data.profit_margin * 100).toFixed(2)}%` : "—"} />
              <Stat label={t("stat.beta")} value={fmt(fund.data?.beta)} />
              <Stat label={t("stat.high52")} value={fmt(fund.data?.fifty_two_week_high)} />
              <Stat label={t("stat.low52")} value={fmt(fund.data?.fifty_two_week_low)} />
            </div>
            {fund.data?.summary && (
              <details className="mt-4">
                <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-300">{t("stock.businessSummary")}</summary>
                <p className="mt-2 text-xs text-zinc-400 leading-relaxed max-h-48 overflow-y-auto">{fund.data.summary}</p>
              </details>
            )}
          </Card>

          <Card>
            <CardHeader title={t("stock.news")} />
            <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
              {(news.data?.items ?? []).map((n, i) => (
                <a key={i} href={n.url ?? "#"} target="_blank" rel="noreferrer"
                   className="block group rounded-lg p-3 hover:bg-white/[0.04] border border-transparent hover:border-white/5 transition">
                  <div className="text-sm text-zinc-100 group-hover:text-cyan-300 line-clamp-2">{n.title}</div>
                  <div className="text-[10px] text-zinc-500 mt-1">
                    {n.publisher ?? "—"}{n.published ? ` · ${String(n.published).slice(0, 16)}` : ""}
                  </div>
                </a>
              ))}
              {!news.isLoading && (news.data?.items?.length ?? 0) === 0 && (
                <div className="text-xs text-zinc-500">{t("stock.noNews")}</div>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Sharing toolbar */}
      <ShareSummary
        symbol={quote.data?.symbol ?? symbol}
        name={quote.data?.name ?? fund.data?.name ?? ""}
        market={quote.data?.market}
        price={quote.data?.price}
        currency={quote.data?.currency}
        change_pct={quote.data?.change_pct}
        signals={ind.data?.signals}
      />

      {/* Committee */}
      <CommitteePanel symbol={quote.data?.symbol ?? symbol} />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</div>
      <div className="font-mono text-zinc-100 mt-0.5">{value ?? "—"}</div>
    </div>
  );
}

function signalTone(v: string): "bull" | "bear" | "warn" | "info" | "default" {
  const s = v.toLowerCase();
  if (s.includes("oversold") || s.includes("golden") || s.includes("bullish") || s.includes("compressed")) return "bull";
  if (s.includes("overbought") || s.includes("death") || s.includes("bearish") || s.includes("extended")) return "bear";
  if (s.includes("neutral") || s.includes("mid")) return "default";
  return "info";
}
