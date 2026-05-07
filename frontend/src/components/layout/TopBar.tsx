import { useEffect, useState } from "react";
import { Activity, Sparkles, Sun, Moon, Languages } from "lucide-react";
import { api, type Capabilities } from "@/api/client";
import { Badge } from "@/components/ui/Badge";
import { useTheme } from "@/lib/theme";
import { useI18n } from "@/lib/i18n";
import { SearchBar } from "./SearchBar";

export function TopBar() {
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const { theme, toggle: toggleTheme } = useTheme();
  const { lang, toggle: toggleLang, t } = useI18n();

  useEffect(() => {
    api.capabilities().then(setCaps).catch(() => {});
  }, []);

  return (
    <header className="border-b border-white/5 bg-black/10 backdrop-blur sticky top-0 z-30">
      <div className="flex items-center gap-4 px-6 py-3">
        <div className="flex-1 max-w-2xl">
          <SearchBar />
        </div>
        <div className="hidden md:flex items-center gap-2">
          <Badge tone="info">
            <Activity className="w-3 h-3 mr-1" />
            <span className="live-dot mr-1" />
            {t("topbar.live")}
          </Badge>
          {caps?.llm.configured ? (
            <Badge tone="bull">
              <Sparkles className="w-3 h-3 mr-1" />
              {caps.llm.provider} · {caps.llm.model}
            </Badge>
          ) : (
            <Badge tone="warn">{t("topbar.demo")}</Badge>
          )}
        </div>
        <div className="flex items-center gap-1">
          <IconBtn onClick={toggleLang} aria-label={t("settings.toolbar.lang")}>
            <Languages className="w-4 h-4" />
            <span className="ml-1.5 text-[11px] font-medium uppercase tracking-wider">{lang}</span>
          </IconBtn>
          <IconBtn onClick={toggleTheme} aria-label={t("settings.toolbar.theme")}>
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </IconBtn>
        </div>
      </div>
    </header>
  );
}

function IconBtn({ children, onClick, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      onClick={onClick}
      className="h-9 px-2.5 inline-flex items-center rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-white/5 transition-colors"
      {...rest}
    >
      {children}
    </button>
  );
}
