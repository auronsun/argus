/**
 * Build a single Markdown document from a completed (or partial) committee
 * run, including the verdict synthesis AND each analyst's full commentary.
 *
 * Lives outside CommitteePanel so the export shape can be reused (e.g. by a
 * future "Recent analyses" history view) without duplicating string-building.
 */
import type { RunState } from "./committee-store";
import { disclaimer, stockShareUrl } from "./share";

const ANALYST_ROLES = [
  { key: "technical",   i18n: "agent.technical.name" },
  { key: "fundamental", i18n: "agent.fundamental.name" },
  { key: "sentiment",   i18n: "agent.sentiment.name" },
  { key: "macro",       i18n: "agent.macro.name" },
  { key: "risk",        i18n: "agent.risk.name" },
  { key: "flow",        i18n: "agent.flow.name" },
] as const;

type Translator = (key: string, vars?: Record<string, string | number>) => string;

export function buildAnalysisMarkdown(
  state: RunState,
  symbol: string,
  t: Translator,
  lang: "en" | "zh"
): string {
  const lines: string[] = [];
  const v = state.verdict;

  // -- Header -------------------------------------------------------------
  lines.push(`# ${symbol} — ${t("comm.title")}`);
  if (state.completedAt) {
    lines.push("");
    lines.push(`*${new Date(state.completedAt).toLocaleString()}*`);
  }
  lines.push("");

  // -- Verdict synthesis --------------------------------------------------
  if (v) {
    const action = (v.action || "—").toUpperCase();
    const tagline: string[] = [`**${action}**`];
    if (typeof v.conviction === "number") tagline.push(`conviction ${v.conviction}/5`);
    if (v.horizon) tagline.push(`${t("comm.horizon")} ${v.horizon}`);

    lines.push(`## ${t("comm.synthesis")}`);
    lines.push("");
    lines.push(tagline.join(" · "));
    lines.push("");

    if (v.entry_zone) lines.push(`- **${t("comm.entryZone")}:** ${v.entry_zone}`);
    if (v.stop_zone)  lines.push(`- **${t("comm.stopZone")}:** ${v.stop_zone}`);
    if (v.entry_zone || v.stop_zone) lines.push("");

    if (v.thesis) {
      lines.push(`### ${t("share.export.thesis")}`);
      lines.push("");
      lines.push(v.thesis);
      lines.push("");
    }

    if (v.key_risks && v.key_risks.length > 0) {
      lines.push(`### ${t("comm.keyRisks")}`);
      lines.push("");
      for (const r of v.key_risks) lines.push(`- ${r}`);
      lines.push("");
    }

    if ((v.conviction ?? 5) <= 2) {
      lines.push(`> ⚠ ${t("share.lowConviction")}`);
      lines.push("");
    }

    lines.push("---");
    lines.push("");
  }

  // -- Per-analyst commentary --------------------------------------------
  const hasAny = ANALYST_ROLES.some((r) => (state.agents[r.key]?.text ?? "").trim().length > 0);
  const hasErrored = ANALYST_ROLES.some((r) => state.agents[r.key]?.status === "error");

  if (hasAny || hasErrored) {
    lines.push(`## ${t("share.export.analystCommentary")}`);
    lines.push("");
    for (const r of ANALYST_ROLES) {
      const a = state.agents[r.key];
      const txt = (a?.text ?? "").trim();
      if (!txt && a?.status !== "error") continue;
      lines.push(`### ${t(r.i18n)}`);
      lines.push("");
      if (a?.status === "error" && !txt) {
        lines.push(`> _${t("share.export.agentFailed")}_`);
      } else {
        lines.push(txt);
      }
      lines.push("");
    }
  }

  // -- Footer -------------------------------------------------------------
  lines.push("---");
  lines.push(`Source: ${stockShareUrl(symbol)}`);
  lines.push("");
  lines.push(`> _${disclaimer(lang)}_`);
  return lines.join("\n");
}
