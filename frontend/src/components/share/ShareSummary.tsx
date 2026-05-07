import { useState } from "react";
import { Copy, Link2, Check } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useI18n } from "@/lib/i18n";
import { copyText, disclaimer, stockShareUrl } from "@/lib/share";
import { fmt, fmtPct } from "@/lib/cn";

interface Props {
  symbol: string;
  name: string;
  market?: string;
  price?: number;
  currency?: string;
  change_pct?: number;
  signals?: Record<string, string>;
}

export function ShareSummary(p: Props) {
  const { t, lang } = useI18n();
  const [copied, setCopied] = useState<"summary" | "link" | null>(null);

  function buildSummary(): string {
    const lines: string[] = [];
    lines.push(`# ${p.symbol}${p.name ? " · " + p.name : ""}`);
    if (p.market) lines.push(`**Market:** ${p.market}`);
    if (typeof p.price === "number") {
      lines.push(`**Price:** ${fmt(p.price)} ${p.currency ?? ""}  (${fmtPct(p.change_pct)})`);
    }
    if (p.signals && Object.keys(p.signals).length) {
      lines.push("");
      lines.push("**Technical signals**");
      for (const [k, v] of Object.entries(p.signals)) {
        lines.push(`- ${k}: ${v}`);
      }
    }
    lines.push("");
    lines.push(`Source: ${stockShareUrl(p.symbol)}`);
    lines.push("");
    lines.push(`> _${disclaimer(lang)}_`);
    return lines.join("\n");
  }

  async function copySummary() {
    if (await copyText(buildSummary())) {
      setCopied("summary");
      setTimeout(() => setCopied(null), 1400);
    }
  }
  async function copyLink() {
    if (await copyText(stockShareUrl(p.symbol))) {
      setCopied("link");
      setTimeout(() => setCopied(null), 1400);
    }
  }

  return (
    <Card className="!py-3 !px-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="text-xs text-zinc-500">{t("share.disclaimer")}</div>
        <div className="flex gap-2">
          <Button variant="subtle" onClick={copySummary} className="!px-3 !py-1.5 text-xs">
            {copied === "summary" ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
            {copied === "summary" ? t("share.copied") : t("share.copySummary")}
          </Button>
          <Button variant="subtle" onClick={copyLink} className="!px-3 !py-1.5 text-xs">
            {copied === "link" ? <Check className="w-3 h-3" /> : <Link2 className="w-3 h-3" />}
            {copied === "link" ? t("share.copied") : t("share.shareLink")}
          </Button>
        </div>
      </div>
    </Card>
  );
}
