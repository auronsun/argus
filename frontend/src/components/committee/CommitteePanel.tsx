import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Play, RotateCcw, Download, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useI18n } from "@/lib/i18n";
import { downloadText } from "@/lib/share";
import { buildAnalysisMarkdown } from "@/lib/committee-export";
import {
  committeeStore,
  initAgents,
  type AgentState,
  type RunState,
} from "@/lib/committee-store";
import { AgentCard } from "./AgentCard";

export function CommitteePanel({ symbol }: { symbol: string }) {
  const { t, lang } = useI18n();
  const [state, setState] = useState<RunState | null>(() =>
    committeeStore.get(symbol, lang)
  );

  // Subscribe whenever the (symbol, lang) tuple we care about changes.
  // Critically, we DO NOT close the connection on unmount — only the
  // listener subscription. The run lives in the singleton store.
  useEffect(() => {
    const unsub = committeeStore.subscribe(symbol, lang, setState);
    return unsub;
  }, [symbol, lang]);

  const running = state?.running ?? false;
  const verdict = state?.verdict ?? null;
  const agents: Record<string, AgentState> = state?.agents ?? initAgents();

  function start() { committeeStore.start(symbol, lang); }
  function reset() { committeeStore.reset(symbol, lang); }

  return (
    <Card className="!p-0">
      <div className="p-5 flex items-center justify-between border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-violet-500 to-pink-500 grid place-items-center">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="text-sm font-medium">{t("comm.title")}</div>
            <div className="text-xs text-zinc-500">{t("comm.subtitle")}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {running ? (
            <Badge tone="info"><span className="live-dot mr-1" /> {t("comm.deliberating")}</Badge>
          ) : verdict ? (
            <Badge tone="bull">{t("comm.verdictReady")}</Badge>
          ) : null}
          {!running && (
            <Button onClick={start} variant="primary">
              <Play className="w-3.5 h-3.5" /> {t("comm.run")}
            </Button>
          )}
          {(running || verdict || state) && (
            <Button onClick={reset} variant="outline" title={running ? "stop" : "clear"}>
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </div>

      <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-3">
        {(["technical", "fundamental", "sentiment", "macro", "risk", "flow"] as const).map((r) => (
          <AgentCard key={r} agent={agents[r]} />
        ))}
      </div>

      <div className="p-5 border-t border-white/5">
        <CardHeader title={t("comm.synthesis")} />
        {/* CIO emits raw JSON tokens — hide them; the VerdictCard below renders
            the structured payload nicely. The card header still shows progress. */}
        <AgentCard agent={agents.cio} hideText />
        <AnimatePresence>
          {state?.verdict && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-4"
            >
              <VerdictCard state={state} symbol={symbol} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Card>
  );
}

function VerdictCard({ state, symbol }: { state: RunState; symbol: string }) {
  const { t, lang } = useI18n();
  const v = state.verdict!;
  const action = (v.action || "—").toUpperCase();
  const tone =
    action.includes("BUY") || action.includes("ACCUMULATE") ? "bull"
    : action.includes("SELL") || action.includes("TRIM") ? "bear"
    : "warn";
  const conviction = v.conviction ?? 0;
  const lowConviction = conviction > 0 && conviction <= 2;

  function exportMarkdown() {
    const md = buildAnalysisMarkdown(state, symbol, t, lang);
    downloadText(
      `argus-analysis-${symbol}-${new Date().toISOString().slice(0, 10)}.md`,
      md
    );
  }

  return (
    <div className="rounded-2xl p-5 border border-white/10 bg-gradient-to-br from-violet-500/10 via-transparent to-cyan-500/10">
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <Badge tone={tone as any} className="text-sm !px-3 !py-1">{action}</Badge>
        <Badge>{t("comm.horizon")} · {v.horizon ?? "—"}</Badge>
        <Button variant="subtle" onClick={exportMarkdown} className="!ml-auto !px-3 !py-1.5 text-xs">
          <Download className="w-3 h-3" /> {t("share.exportMarkdown")}
        </Button>
        <div className="flex items-center gap-1 text-xs text-zinc-400">
          {t("comm.conviction")}
          <div className="flex gap-0.5 ml-1">
            {[1, 2, 3, 4, 5].map((i) => (
              <span
                key={i}
                className={`w-3 h-1.5 rounded-full ${i <= conviction ? "bg-gradient-to-r from-violet-400 to-cyan-400" : "bg-white/10"}`}
              />
            ))}
          </div>
        </div>
      </div>
      {lowConviction && (
        <div className="mb-3 flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-200">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          <span>{t("share.lowConviction")}</span>
        </div>
      )}
      {v.thesis && <p className="text-sm text-zinc-200 leading-relaxed">{v.thesis}</p>}
      {(v.entry_zone || v.stop_zone) && (
        <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-lg p-3 bg-emerald-500/5 border border-emerald-500/20">
            <div className="text-emerald-300 uppercase tracking-wider text-[10px] mb-1">{t("comm.entryZone")}</div>
            <div className="font-mono text-emerald-200">{v.entry_zone ?? "—"}</div>
          </div>
          <div className="rounded-lg p-3 bg-rose-500/5 border border-rose-500/20">
            <div className="text-rose-300 uppercase tracking-wider text-[10px] mb-1">{t("comm.stopZone")}</div>
            <div className="font-mono text-rose-200">{v.stop_zone ?? "—"}</div>
          </div>
        </div>
      )}
      {v.key_risks && v.key_risks.length > 0 && (
        <div className="mt-3">
          <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">{t("comm.keyRisks")}</div>
          <ul className="text-xs text-zinc-300 space-y-1">
            {v.key_risks.map((r, i) => <li key={i}>· {r}</li>)}
          </ul>
        </div>
      )}
      {v.raw && !v.thesis && (
        <pre className="text-xs text-zinc-400 whitespace-pre-wrap mt-3">{v.raw}</pre>
      )}
      <div className="mt-3 text-[10px] text-zinc-500 italic">{t("share.disclaimer")}</div>
    </div>
  );
}
