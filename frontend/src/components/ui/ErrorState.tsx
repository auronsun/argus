import { AlertTriangle, RefreshCcw } from "lucide-react";
import { ApiError } from "@/api/client";
import { Button } from "./Button";
import { useT } from "@/lib/i18n";

export function ErrorState({
  error,
  onRetry,
  compact = false,
}: {
  error: unknown;
  onRetry?: () => void;
  compact?: boolean;
}) {
  const t = useT();
  const detail =
    error instanceof ApiError ? error.detail : (error instanceof Error ? error.message : String(error));
  const kind = error instanceof ApiError ? error.kind : "unknown";

  const headline =
    kind === "network"   ? t("error.network")  :
    kind === "upstream"  ? t("error.upstream") :
    kind === "validation"? t("error.validation") :
                           t("error.unknown");

  return (
    <div
      className={
        "rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 flex items-start gap-3 " +
        (compact ? "text-xs" : "text-sm")
      }
    >
      <AlertTriangle className="w-4 h-4 mt-0.5 text-amber-300 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-amber-200 font-medium">{headline}</div>
        <div className="text-zinc-400 mt-0.5 break-words">{detail}</div>
      </div>
      {onRetry && (
        <Button onClick={onRetry} variant="outline" className="!px-3 !py-1.5 text-xs">
          <RefreshCcw className="w-3 h-3" /> {t("error.retry")}
        </Button>
      )}
    </div>
  );
}
