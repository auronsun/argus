import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, Eye, EyeOff, Save, Trash2, Sparkles, Zap } from "lucide-react";
import { api, type KeyEntry, type KeysStatus, type SmokeTestResult } from "@/api/client";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { useT } from "@/lib/i18n";

interface LLMSlot {
  /** Display label */
  label: string;
  /** Slot name for the secret (key for cloud providers, host URL for ollama) */
  keySlot: string;
  /** Whether the secret is a host URL rather than an API key */
  isHost?: boolean;
  /** Slot name for the model override */
  modelSlot: string;
  helper?: string;
}

interface DataSlot {
  label: string;
  slot: string;
  helper?: string;
  /** Whether the backend supports a smoke test for this slot. */
  smokeTestable?: boolean;
}

const LLM_SLOTS: LLMSlot[] = [
  { label: "Anthropic",        keySlot: "anthropic",   modelSlot: "anthropic_model", helper: "claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5…" },
  { label: "OpenAI",           keySlot: "openai",      modelSlot: "openai_model",    helper: "gpt-5.5, gpt-5.5-pro, gpt-5.5-mini…" },
  { label: "DeepSeek",         keySlot: "deepseek",    modelSlot: "deepseek_model",  helper: "deepseek-v4-pro, deepseek-v4-flash (deepseek-chat / -reasoner deprecated 2026-07-24)" },
  { label: "Qwen (DashScope)", keySlot: "qwen",        modelSlot: "qwen_model",      helper: "qwen-plus, qwen-max…" },
  { label: "NVIDIA NIM",       keySlot: "nvidia",      modelSlot: "nvidia_model",    helper: "minimaxai/minimax-m2.7, meta/llama-3.3-70b-instruct, nvidia/llama-3.1-nemotron-70b-instruct…" },
  { label: "Ollama (local)",   keySlot: "ollama_host", modelSlot: "ollama_model",    helper: "host URL + local model name", isHost: true },
];

const DATA_SLOTS: DataSlot[] = [
  { label: "Alpha Vantage",  slot: "alpha_vantage",     smokeTestable: true },
  { label: "Finnhub",        slot: "finnhub",            smokeTestable: true },
  { label: "Tushare Pro",    slot: "tushare",            smokeTestable: true,  helper: "for full A-share history" },
  { label: "Longbridge",     slot: "longbridge_token",   smokeTestable: false, helper: "access token for HK realtime · smoke test not yet available" },
];

export function Settings() {
  const t = useT();
  const { data: caps } = useQuery({ queryKey: ["caps"], queryFn: api.capabilities });
  const { data: keys } = useQuery<KeysStatus>({ queryKey: ["keys"], queryFn: api.keysGet });

  return (
    <div className="px-6 py-6 grid lg:grid-cols-2 gap-6">
      <Card>
        <CardHeader title={t("settings.llm.title")} subtitle={t("settings.llm.subtitle")} />
        <div className="space-y-3">
          {LLM_SLOTS.map((s) => (
            <LLMRow key={s.keySlot} slot={s} entry={keys?.providers[s.keySlot]} />
          ))}
        </div>
        <div className="mt-5 pt-4 border-t border-white/5 flex items-center gap-2">
          <span className="text-xs text-zinc-500">{t("settings.active")}:</span>
          {keys?.active_llm ? (
            <Badge tone="bull">
              <Sparkles className="w-3 h-3 mr-1" />
              {keys.active_llm.provider} · {keys.active_llm.model}
            </Badge>
          ) : (
            <Badge tone="warn">{t("settings.demoMode")}</Badge>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title={t("settings.data.title")} subtitle={t("settings.data.subtitle")} />
        <div className="space-y-3">
          {DATA_SLOTS.map((s) => (
            <DataRow key={s.slot} slot={s} entry={keys?.providers[s.slot]} />
          ))}
        </div>
        <div className="mt-5 pt-4 border-t border-white/5 text-xs text-zinc-500">
          {t("settings.noKey")}
        </div>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader title={t("settings.about.title")} />
        <div className="text-sm text-zinc-300 leading-relaxed space-y-2 max-w-3xl">
          <p>{t("settings.about.body", { v: caps?.version ?? "—", markets: (caps?.markets ?? []).join(" · ") })}</p>
          <p className="text-zinc-500">{t("settings.about.disclaimer")}</p>
        </div>
      </Card>
    </div>
  );
}

function LLMRow({ slot, entry }: { slot: LLMSlot; entry: KeyEntry | undefined }) {
  const t = useT();
  const qc = useQueryClient();

  const [model, setModel] = useState("");
  const [secret, setSecret] = useState("");
  const [show, setShow] = useState(false);
  const [savedTick, setSavedTick] = useState(false);
  const [testResult, setTestResult] = useState<SmokeTestResult | null>(null);

  // Populate the model field from the effective value (env or UI)
  useEffect(() => { setModel(entry?.model ?? ""); }, [entry?.model, entry?.model_source]);
  useEffect(() => { setSecret(""); }, [entry?.source]);
  // Drop a stale result when the key/model changes — it no longer matches.
  useEffect(() => { setTestResult(null); }, [entry?.source, entry?.model_source, entry?.model]);

  const update = useMutation({
    mutationFn: () => {
      const updates: Record<string, string> = {};
      if (secret.trim()) updates[slot.keySlot] = secret.trim();
      if (model.trim() && model.trim() !== (entry?.model ?? "")) updates[slot.modelSlot] = model.trim();
      // Allow user to "save just the model" without re-entering the key
      if (Object.keys(updates).length === 0 && model.trim()) updates[slot.modelSlot] = model.trim();
      return api.keysUpdate(updates);
    },
    onSuccess: () => {
      setSecret("");
      setSavedTick(true);
      setTimeout(() => setSavedTick(false), 1400);
      qc.invalidateQueries({ queryKey: ["keys"] });
      qc.invalidateQueries({ queryKey: ["caps"] });
    },
  });
  const clearKey = useMutation({
    mutationFn: async () => {
      await api.keysClear(slot.keySlot);
      // Clearing the key should leave the model alone — that's still a valid override
      return api.keysGet();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["keys"] });
      qc.invalidateQueries({ queryKey: ["caps"] });
    },
  });

  const test = useMutation({
    mutationFn: () => api.keysTest(slot.keySlot),
    onSuccess: (r) => setTestResult(r),
    onError: (e: any) =>
      setTestResult({ ok: false, kind: "unknown", detail: e?.detail ?? e?.message ?? String(e) }),
  });

  const keyPlaceholder = slot.isHost ? t("settings.field.placeholderHost") : t("settings.field.placeholder");
  const dirty =
    (secret.trim().length > 0) ||
    (model.trim() !== (entry?.model ?? "") && model.trim().length > 0);

  return (
    <div className="rounded-xl border border-white/5 px-4 py-3">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-zinc-200">{slot.label}</span>
          {entry?.configured ? (
            <Badge tone={entry.source === "ui" ? "info" : "default"}>
              <Check className="w-3 h-3 mr-1" />
              {entry.source === "ui" ? t("settings.from.ui") : t("settings.from.env")}
            </Badge>
          ) : (
            <Badge>{t("settings.notSet")}</Badge>
          )}
          {entry?.model && (
            <Badge tone={entry.model_source === "ui" ? "info" : "default"}>
              {entry.model_source === "ui" ? t("settings.from.uiModel") : t("settings.from.envModel")}
            </Badge>
          )}
        </div>
        {savedTick && <span className="text-xs text-emerald-400">✓ saved</span>}
      </div>
      {slot.helper && <div className="text-[11px] text-zinc-500 mb-2">{slot.helper}</div>}

      <form
        onSubmit={(e) => { e.preventDefault(); if (dirty) update.mutate(); }}
        className="space-y-2"
      >
        {/* Model row */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-zinc-500 w-12 shrink-0">
            {t("settings.field.modelLabel")}
          </span>
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="—"
            className="flex-1 h-9 px-3 rounded-lg glass text-sm outline-none font-mono"
          />
        </div>

        {/* Key / Host row */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-zinc-500 w-12 shrink-0">
            {slot.isHost ? t("settings.field.hostLabel") : t("settings.field.keyLabel")}
          </span>
          <div className="relative flex-1">
            <input
              type={show || slot.isHost ? "text" : "password"}
              autoComplete="off"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder={keyPlaceholder}
              className="w-full h-9 pl-3 pr-9 rounded-lg glass text-sm outline-none font-mono"
            />
            {!slot.isHost && (
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-200"
                aria-label={show ? "hide" : "show"}
              >
                {show ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            )}
          </div>
          <Button type="submit" variant="primary" disabled={!dirty || update.isPending}>
            <Save className="w-3.5 h-3.5" /> {t("settings.save")}
          </Button>
          {entry?.configured && (
            <Button
              type="button"
              variant="outline"
              onClick={() => test.mutate()}
              disabled={test.isPending}
              title={t("settings.test")}
            >
              {test.isPending ? <Spinner className="!w-3.5 !h-3.5" /> : <Zap className="w-3.5 h-3.5" />}
              {test.isPending ? t("settings.testing") : t("settings.test")}
            </Button>
          )}
          {entry?.configured && entry.source === "ui" && (
            <Button type="button" variant="outline" onClick={() => clearKey.mutate()} disabled={clearKey.isPending}>
              <Trash2 className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </form>

      {testResult && <TestResult result={testResult} />}
    </div>
  );
}

function TestResult({ result }: { result: SmokeTestResult }) {
  const t = useT();
  if (result.ok) {
    return (
      <div className="mt-2 flex items-start gap-2 text-xs">
        <Check className="w-3.5 h-3.5 mt-0.5 text-emerald-400 shrink-0" />
        <div className="flex-1 min-w-0">
          <span className="text-emerald-300">
            {t("settings.test.ok", { latency: result.latency_ms ?? 0 })}
          </span>
          {result.model && <span className="text-zinc-500"> · {result.model}</span>}
          {result.sample && (
            <div className="text-zinc-500 mt-0.5 font-mono truncate">
              {t("settings.test.sample", { sample: result.sample })}
            </div>
          )}
        </div>
      </div>
    );
  }
  return (
    <div className="mt-2 flex items-start gap-2 text-xs">
      <AlertTriangle className="w-3.5 h-3.5 mt-0.5 text-amber-300 shrink-0" />
      <div className="flex-1 min-w-0">
        <span className="text-amber-200">{t(`settings.test.kind.${result.kind}`)}</span>
        {result.model && <span className="text-zinc-500"> · {result.model}</span>}
        {result.detail && (
          <div className="text-zinc-500 mt-0.5 break-words">{result.detail}</div>
        )}
      </div>
    </div>
  );
}

function DataRow({ slot, entry }: { slot: DataSlot; entry: KeyEntry | undefined }) {
  const t = useT();
  const qc = useQueryClient();
  const [value, setValue] = useState("");
  const [show, setShow] = useState(false);
  const [savedTick, setSavedTick] = useState(false);
  const [testResult, setTestResult] = useState<SmokeTestResult | null>(null);

  useEffect(() => { setValue(""); }, [entry?.source]);
  // Stale result when key changes underneath us
  useEffect(() => { setTestResult(null); }, [entry?.source]);

  const update = useMutation({
    mutationFn: () => api.keysUpdate({ [slot.slot]: value }),
    onSuccess: () => {
      setValue("");
      setSavedTick(true);
      setTimeout(() => setSavedTick(false), 1400);
      qc.invalidateQueries({ queryKey: ["keys"] });
      qc.invalidateQueries({ queryKey: ["caps"] });
    },
  });
  const clear = useMutation({
    mutationFn: () => api.keysClear(slot.slot),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["keys"] });
      qc.invalidateQueries({ queryKey: ["caps"] });
    },
  });
  const test = useMutation({
    mutationFn: () => api.keysTest(slot.slot),
    onSuccess: (r) => setTestResult(r),
    onError: (e: any) =>
      setTestResult({ ok: false, kind: "unknown", detail: e?.detail ?? e?.message ?? String(e) }),
  });

  return (
    <div className="rounded-xl border border-white/5 px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-200">{slot.label}</span>
          {entry?.configured ? (
            <Badge tone={entry.source === "ui" ? "info" : "default"}>
              <Check className="w-3 h-3 mr-1" />
              {entry.source === "ui" ? t("settings.from.ui") : t("settings.from.env")}
            </Badge>
          ) : (
            <Badge>{t("settings.notSet")}</Badge>
          )}
        </div>
        {savedTick && <span className="text-xs text-emerald-400">✓ saved</span>}
      </div>
      {slot.helper && <div className="text-[11px] text-zinc-500 mb-2">{slot.helper}</div>}
      <form
        onSubmit={(e) => { e.preventDefault(); if (value.trim()) update.mutate(); }}
        className="flex gap-2"
      >
        <div className="relative flex-1">
          <input
            type={show ? "text" : "password"}
            autoComplete="off"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={t("settings.field.placeholder")}
            className="w-full h-9 pl-3 pr-9 rounded-lg glass text-sm outline-none font-mono"
          />
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-200"
            aria-label={show ? "hide" : "show"}
          >
            {show ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          </button>
        </div>
        <Button type="submit" variant="primary" disabled={!value.trim() || update.isPending}>
          <Save className="w-3.5 h-3.5" /> {t("settings.save")}
        </Button>
        {entry?.configured && slot.smokeTestable && (
          <Button
            type="button"
            variant="outline"
            onClick={() => test.mutate()}
            disabled={test.isPending}
            title={t("settings.test")}
          >
            {test.isPending ? <Spinner className="!w-3.5 !h-3.5" /> : <Zap className="w-3.5 h-3.5" />}
            {test.isPending ? t("settings.testing") : t("settings.test")}
          </Button>
        )}
        {entry?.configured && entry.source === "ui" && (
          <Button type="button" variant="outline" onClick={() => clear.mutate()} disabled={clear.isPending}>
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        )}
      </form>

      {testResult && <TestResult result={testResult} />}
    </div>
  );
}
