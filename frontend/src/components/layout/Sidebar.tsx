import { NavLink } from "react-router-dom";
import { LayoutDashboard, History, Filter, Star, Settings, Github } from "lucide-react";
import { cn } from "@/lib/cn";
import { useT } from "@/lib/i18n";

export function Sidebar() {
  const t = useT();
  const items = [
    { to: "/", labelKey: "nav.dashboard", icon: LayoutDashboard, end: true },
    { to: "/history", labelKey: "nav.history", icon: History },
    { to: "/screener", labelKey: "nav.screener", icon: Filter },
    { to: "/watchlist", labelKey: "nav.watchlist", icon: Star },
    { to: "/settings", labelKey: "nav.settings", icon: Settings },
  ];

  return (
    <aside className="w-60 shrink-0 border-r border-white/5 bg-black/20 flex flex-col">
      <div className="px-5 py-5 flex items-center gap-3">
        <div className="relative w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-400 grid place-items-center shadow-[0_0_30px_-6px_rgba(124,58,237,0.7)]">
          <span className="text-base font-black text-white">A</span>
          <span className="absolute -inset-px rounded-xl ring-1 ring-white/20" />
        </div>
        <div>
          <div className="font-semibold tracking-tight">Argus</div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500">{t("app.tagline")}</div>
        </div>
      </div>

      <nav className="flex-1 px-3 space-y-1">
        {items.map(({ to, labelKey, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                isActive
                  ? "bg-white/[0.06] text-zinc-100 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.06)]"
                  : "text-zinc-400 hover:text-zinc-100 hover:bg-white/[0.03]"
              )
            }
          >
            <Icon className="w-4 h-4" strokeWidth={1.75} />
            <span>{t(labelKey)}</span>
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-white/5">
        <a
          href="https://github.com"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-200 transition-colors"
        >
          <Github className="w-3.5 h-3.5" />
          {t("sidebar.starGithub")}
        </a>
        <div className="text-[10px] text-zinc-600 mt-1">{t("sidebar.versionLine")}</div>
      </div>
    </aside>
  );
}
