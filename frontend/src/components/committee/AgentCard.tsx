import { motion } from "framer-motion";
import { Activity, BarChart3, Newspaper, Globe2, Shield, Target, Bot, Waves, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import { useT } from "@/lib/i18n";
import { Spinner } from "@/components/ui/Spinner";

interface RoleTheme {
  gradient: string;
  glow: string;
  iconBg: string;
  iconColor: string;
  Icon: LucideIcon;
  i18n: string;
}

const ROLE_THEME: Record<string, RoleTheme> = {
  technical:   { gradient: "from-cyan-500/15 to-cyan-500/0",     glow: "shadow-cyan-500/20",    iconBg: "bg-cyan-500/15",    iconColor: "text-cyan-300",    Icon: Activity,  i18n: "agent.technical.name"   },
  fundamental: { gradient: "from-emerald-500/15 to-emerald-500/0", glow: "shadow-emerald-500/20", iconBg: "bg-emerald-500/15", iconColor: "text-emerald-300", Icon: BarChart3, i18n: "agent.fundamental.name" },
  sentiment:   { gradient: "from-pink-500/15 to-pink-500/0",     glow: "shadow-pink-500/20",    iconBg: "bg-pink-500/15",    iconColor: "text-pink-300",    Icon: Newspaper, i18n: "agent.sentiment.name"   },
  macro:       { gradient: "from-amber-500/15 to-amber-500/0",   glow: "shadow-amber-500/20",   iconBg: "bg-amber-500/15",   iconColor: "text-amber-300",   Icon: Globe2,    i18n: "agent.macro.name"       },
  risk:        { gradient: "from-rose-500/15 to-rose-500/0",     glow: "shadow-rose-500/20",    iconBg: "bg-rose-500/15",    iconColor: "text-rose-300",    Icon: Shield,    i18n: "agent.risk.name"        },
  flow:        { gradient: "from-sky-500/15 to-sky-500/0",       glow: "shadow-sky-500/20",     iconBg: "bg-sky-500/15",     iconColor: "text-sky-300",     Icon: Waves,     i18n: "agent.flow.name"        },
  cio:         { gradient: "from-violet-500/20 to-violet-500/0", glow: "shadow-violet-500/30",  iconBg: "bg-violet-500/15",  iconColor: "text-violet-300",  Icon: Target,    i18n: "agent.cio.name"         },
};

export interface AgentState {
  role: string;
  status: "idle" | "thinking" | "done" | "error";
  text: string;
}

export function AgentCard({ agent, hideText = false }: { agent: AgentState; hideText?: boolean }) {
  const t = useT();
  const theme = ROLE_THEME[agent.role] ?? {
    gradient: "", glow: "", iconBg: "bg-white/10", iconColor: "text-zinc-300",
    Icon: Bot, i18n: agent.role,
  };
  const Icon = theme.Icon;
  const statusKey =
    agent.status === "thinking" ? "agent.status.thinking" :
    agent.status === "done" ? "agent.status.done" :
    agent.status === "error" ? "agent.status.error" : "agent.status.queued";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "relative rounded-2xl p-4 glass overflow-hidden",
        agent.status === "thinking" && `shadow-[0_0_50px_-20px] ${theme.glow}`
      )}
    >
      <div className={cn("absolute inset-0 bg-gradient-to-br pointer-events-none opacity-60", theme.gradient)} />
      <div className="relative">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn("w-9 h-9 rounded-lg grid place-items-center", theme.iconBg)}>
              <Icon className={cn("w-4 h-4", theme.iconColor)} strokeWidth={1.75} />
            </div>
            <div>
              <div className="text-sm font-medium text-zinc-100">{t(theme.i18n)}</div>
              <div className="text-[10px] uppercase tracking-wider text-zinc-500">{t(statusKey)}</div>
            </div>
          </div>
          {agent.status === "thinking" && <Spinner />}
          {agent.status === "done" && <span className="text-emerald-400 text-xs">●</span>}
        </div>
        {!hideText && (
          <div className="mt-3 text-sm leading-relaxed text-zinc-300 whitespace-pre-wrap min-h-[1em] max-h-[260px] overflow-y-auto pr-1">
            {agent.text}
            {agent.status === "thinking" && (
              <span className="inline-block w-2 h-4 bg-cyan-400/70 align-middle ml-0.5 animate-pulse" />
            )}
            {/* Some providers (esp. NVIDIA NIM free tier) close the stream
                cleanly without emitting any tokens. We surface that as an
                explicit "(no content returned)" rather than rendering a
                deceptively-blank "done" card. */}
            {agent.status === "done" && agent.text.trim() === "" && (
              <span className="italic text-zinc-500">{t("agent.noOutput")}</span>
            )}
            {agent.status === "error" && agent.text.trim() === "" && (
              <span className="italic text-rose-300">{t("agent.runFailed")}</span>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
