import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Filter, TrendingDown, TrendingUp, Globe2 } from "lucide-react";
import { api } from "@/api/client";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { MarketBadge } from "@/components/ui/MarketBadge";
import { Spinner } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { changeClass, fmt, fmtPct } from "@/lib/cn";
import { useT } from "@/lib/i18n";

export function Screener() {
  const t = useT();
  const [preset, setPreset] = useState("all");
  const PRESETS = [
    { key: "momentum", label: t("screener.preset.momentum"), icon: <TrendingUp className="w-3.5 h-3.5" /> },
    { key: "oversold", label: t("screener.preset.oversold"), icon: <TrendingDown className="w-3.5 h-3.5" /> },
    { key: "all",      label: t("screener.preset.all"),      icon: <Globe2 className="w-3.5 h-3.5" /> },
  ];
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["screener", preset],
    queryFn: () => api.screenerPreset(preset),
  });

  return (
    <div className="px-6 py-6 space-y-6">
      <Card>
        <CardHeader
          title={t("screener.title")}
          subtitle={t("screener.subtitle")}
          right={<Filter className="w-4 h-4 text-zinc-400" />}
        />
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <Button
              key={p.key}
              variant={preset === p.key ? "primary" : "subtle"}
              onClick={() => setPreset(p.key)}
            >
              {p.icon} {p.label}
            </Button>
          ))}
        </div>
      </Card>

      {isError && (
        <ErrorState error={error} onRetry={() => refetch()} />
      )}

      <Card className="!p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[10px] uppercase tracking-wider text-zinc-500">
              <tr className="border-b border-white/5">
                <th className="text-left px-5 py-3">{t("screener.col.symbol")}</th>
                <th className="text-left px-3 py-3">{t("screener.col.name")}</th>
                <th className="text-left px-3 py-3">{t("screener.col.market")}</th>
                <th className="text-right px-3 py-3">{t("screener.col.price")}</th>
                <th className="text-right px-3 py-3">{t("screener.col.change")}</th>
                <th className="text-right px-3 py-3">{t("screener.col.rsi")}</th>
                <th className="text-right px-5 py-3">{t("screener.col.mcap")}</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={7} className="px-5 py-12 text-center"><Spinner /></td></tr>
              )}
              {(data?.rows ?? []).map((r) => (
                <tr key={r.symbol} className="border-b border-white/[0.03] hover:bg-white/[0.03]">
                  <td className="px-5 py-3 font-mono">
                    <Link to={`/stock/${encodeURIComponent(r.symbol)}`} className="text-cyan-300 hover:text-cyan-200">
                      {r.symbol}
                    </Link>
                  </td>
                  <td className="px-3 py-3 text-zinc-300 max-w-[18rem] truncate">{r.name}</td>
                  <td className="px-3 py-3"><MarketBadge market={r.market} /></td>
                  <td className="px-3 py-3 text-right tabular-nums">{fmt(r.price)}</td>
                  <td className={`px-3 py-3 text-right tabular-nums font-medium ${changeClass(r.change_pct)}`}>
                    {fmtPct(r.change_pct)}
                  </td>
                  <td className="px-3 py-3 text-right tabular-nums text-zinc-300">{fmt(r.rsi_14, 1)}</td>
                  <td className="px-5 py-3 text-right tabular-nums text-zinc-400">{fmt(r.market_cap, 0)}</td>
                </tr>
              ))}
              {!isLoading && (data?.rows?.length ?? 0) === 0 && (
                <tr><td colSpan={7} className="px-5 py-12 text-center text-zinc-500">{t("screener.empty")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
