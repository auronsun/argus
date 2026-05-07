import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { History as HistoryIcon, Trash2, ExternalLink, AlertTriangle } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useT } from "@/lib/i18n";
import { listHistory, clearHistory, removeHistory, subscribeHistory, type HistoryEntry } from "@/lib/history";

export function History() {
  const t = useT();
  const [entries, setEntries] = useState<HistoryEntry[]>(() => listHistory());

  useEffect(() => subscribeHistory(setEntries), []);

  return (
    <div className="px-6 py-6 space-y-6">
      <Card>
        <CardHeader
          title={t("history.title")}
          subtitle={t("history.subtitle")}
          right={
            entries.length > 0 ? (
              <Button variant="outline" onClick={() => { if (confirm(t("history.clearConfirm"))) clearHistory(); }}>
                <Trash2 className="w-3.5 h-3.5" /> {t("history.clearAll")}
              </Button>
            ) : null
          }
        />
        {entries.length === 0 ? (
          <div className="py-16 text-center">
            <HistoryIcon className="w-8 h-8 text-zinc-600 mx-auto mb-3" />
            <div className="text-sm text-zinc-400">{t("history.empty")}</div>
            <div className="text-xs text-zinc-500 mt-1">{t("history.emptyHint")}</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {entries.map((e) => <HistoryCard key={`${e.symbol}::${e.lang}::${e.completedAt}`} entry={e} />)}
          </div>
        )}
      </Card>
    </div>
  );
}

function HistoryCard({ entry }: { entry: HistoryEntry }) {
  const t = useT();
  const v = entry.verdict || {};
  const action = (v.action || "—").toUpperCase();
  const tone =
    action.includes("BUY") || action.includes("ACCUMULATE") ? "bull" :
    action.includes("SELL") || action.includes("TRIM") ? "bear" :
    "warn";
  const conviction = v.conviction ?? 0;
  const lowConv = conviction > 0 && conviction <= 2;
  const when = new Date(entry.completedAt);

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors p-4 flex flex-col gap-3"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-mono text-base text-zinc-100">{entry.symbol}</div>
          <div className="text-xs text-zinc-500">
            {when.toLocaleString()} · {entry.lang.toUpperCase()}
          </div>
        </div>
        <button
          onClick={(ev) => { ev.preventDefault(); removeHistory(entry.symbol, entry.lang); }}
          className="text-zinc-500 hover:text-rose-400 transition-colors"
          title={t("history.remove")}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <Badge tone={tone as any} className="!px-2.5 !py-0.5">{action}</Badge>
        {v.horizon && <Badge>{v.horizon}</Badge>}
        <div className="flex gap-0.5 ml-auto">
          {[1, 2, 3, 4, 5].map((i) => (
            <span
              key={i}
              className={`w-2.5 h-1 rounded-full ${i <= conviction ? "bg-gradient-to-r from-violet-400 to-cyan-400" : "bg-white/10"}`}
            />
          ))}
        </div>
      </div>

      {lowConv && (
        <div className="flex items-start gap-1.5 text-[11px] text-amber-300/80">
          <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
          <span>{t("history.lowConvHint")}</span>
        </div>
      )}

      {v.thesis && (
        <p className="text-sm text-zinc-300 leading-relaxed line-clamp-3">{v.thesis}</p>
      )}

      <Link
        to={`/stock/${encodeURIComponent(entry.symbol)}`}
        className="mt-auto inline-flex items-center gap-1.5 text-xs text-cyan-300 hover:text-cyan-200"
      >
        <ExternalLink className="w-3 h-3" /> {t("history.openStock")}
      </Link>
    </motion.div>
  );
}
