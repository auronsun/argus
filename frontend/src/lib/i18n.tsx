import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Lang = "en" | "zh";

const DICT: Record<Lang, Record<string, string>> = {
  en: {
    "app.tagline": "multi-market",

    // Sidebar
    "nav.dashboard": "Dashboard",
    "nav.history": "History",
    "nav.screener": "Screener",
    "nav.watchlist": "Watchlist",
    "nav.settings": "Settings",
    "sidebar.starGithub": "star on github",
    "sidebar.versionLine": "v0.1.0 · MIT licensed",

    // TopBar
    "topbar.live": "live",
    "topbar.demo": "demo · add API key",

    // SearchBar
    "search.placeholder": "Search any ticker — AAPL · 600519 · 0700.HK · Tencent · 茅台",

    // Dashboard
    "dashboard.badge": "multi-agent · multi-market",
    "dashboard.alpha": "v0.1 alpha",
    "dashboard.heroLine1": "Five analysts.",
    "dashboard.heroLine2": "One ticker.",
    "dashboard.heroBrand": "Argus.",
    "dashboard.heroDesc":
      "An open-source AI investment committee for US, A-shares & HK markets. Type a ticker — five specialised analyst agents will debate it in real time, and a Chief Investment Officer will synthesise the answer.",
    "dashboard.try": "Try:",
    "dashboard.cardDeep.title": "Deep Dive",
    "dashboard.cardDeep.tag": "single ticker · full report",
    "dashboard.cardDeep.desc": "Charts, indicators, fundamentals, news — and the AI committee's verdict.",
    "dashboard.cardScreener.title": "Cross-Market Screener",
    "dashboard.cardScreener.tag": "discovery",
    "dashboard.cardScreener.desc": "Filter US / A-shares / HK by valuation, momentum, and technical setup.",
    "dashboard.cardWatch.title": "Watchlist + Alerts",
    "dashboard.cardWatch.tag": "monitor",
    "dashboard.cardWatch.desc": "Track your tickers; alert when price, change %, or RSI crosses a threshold.",
    "dashboard.snapshot": "live snapshot",
    "dashboard.demoNotice":
      "No LLM API key detected. The committee will run in demo mode. Add a key on the Settings page or to .env to enable real analysis.",

    // Stock page
    "stock.priceVolume": "Price · Volume",
    "stock.fundamentals": "Fundamentals",
    "stock.news": "News",
    "stock.signals": "Quick read · technical signals",
    "stock.noSignals": "no signals available",
    "stock.businessSummary": "business summary",
    "stock.noNews": "No news available.",

    "stat.open": "Open",
    "stat.high": "High",
    "stat.low": "Low",
    "stat.prevClose": "Prev Close",
    "stat.volume": "Volume",
    "stat.marketCap": "Mkt Cap",
    "stat.peTrailing": "P/E (TTM)",
    "stat.peForward": "P/E (Fwd)",
    "stat.pb": "P/B",
    "stat.ps": "P/S",
    "stat.divYield": "Div yield",
    "stat.epsTtm": "EPS (TTM)",
    "stat.profitMargin": "Profit margin",
    "stat.beta": "Beta",
    "stat.high52": "52W High",
    "stat.low52": "52W Low",

    // Committee
    "comm.title": "AI Investment Committee",
    "comm.subtitle": "6 analyst agents · synthesised by CIO",
    "comm.deliberating": "deliberating",
    "comm.verdictReady": "verdict ready",
    "comm.run": "Run",
    "comm.synthesis": "Chief Investment Officer · synthesis",
    "comm.entryZone": "entry zone",
    "comm.stopZone": "stop zone",
    "comm.keyRisks": "key risks",
    "comm.horizon": "horizon",
    "comm.conviction": "conviction:",

    // Agents
    "agent.technical.name": "Technical Analyst",
    "agent.fundamental.name": "Fundamental Analyst",
    "agent.sentiment.name": "Sentiment Analyst",
    "agent.macro.name": "Macro Strategist",
    "agent.risk.name": "Risk Manager",
    "agent.flow.name": "Flow Analyst",
    "agent.cio.name": "Chief Investment Officer",
    "agent.status.thinking": "thinking…",
    "agent.status.done": "verdict ready",
    "agent.status.error": "error",
    "agent.status.queued": "queued",
    "agent.noOutput": "(model returned no content — try re-running or switching provider)",
    "agent.runFailed": "(this analyst's run failed — see details in the system log)",
    "agent.retry": "Retry",

    // History page
    "history.title":         "Recent analyses",
    "history.subtitle":      "Verdicts from your previous committee runs are kept locally on this device.",
    "history.empty":         "No analyses yet.",
    "history.emptyHint":     "Run the AI committee on any stock and the verdict will appear here.",
    "history.openStock":     "Open stock page",
    "history.remove":        "Remove from history",
    "history.clearAll":      "Clear all",
    "history.clearConfirm":  "Clear all history? This cannot be undone.",
    "history.lowConvHint":   "Low conviction at the time of this run.",

    // Screener
    "screener.title": "Cross-Market Screener",
    "screener.subtitle": "Scan US · A-shares · HK by setup. (Custom criteria coming next.)",
    "screener.preset.momentum": "Momentum",
    "screener.preset.oversold": "Oversold",
    "screener.preset.all": "All Markets",
    "screener.col.symbol": "Symbol",
    "screener.col.name": "Name",
    "screener.col.market": "Mkt",
    "screener.col.price": "Price",
    "screener.col.change": "Δ %",
    "screener.col.rsi": "RSI",
    "screener.col.mcap": "Mkt Cap",
    "screener.empty": "No matches.",

    // Watchlist
    "watch.title": "Watchlist",
    "watch.subtitle": "Live snapshots refreshed every 30s.",
    "watch.add": "Add",
    "watch.placeholder": "Add ticker — e.g. NVDA, 600519, 0700.HK",
    "watch.empty": "Empty — add a ticker above.",
    "watch.alerts.title": "Alerts",
    "watch.alerts.subtitle": "Rule-based; evaluate on demand or via cron.",
    "watch.alerts.add": "Add alert",
    "watch.alerts.evaluate": "Evaluate now",
    "watch.alerts.empty": "No alerts yet.",
    "watch.alerts.symbol": "Symbol",
    "watch.alerts.value": "value",
    "watch.alerts.metric.price": "price",
    "watch.alerts.metric.changePct": "Δ %",
    "watch.alerts.metric.rsi": "RSI(14)",
    "watch.alerts.none": "No alerts triggered.",
    "watch.alerts.triggered": "{n} triggered.",

    // Settings
    "settings.llm.title": "LLM Providers",
    "settings.llm.subtitle": "Paste a key to enable real AI committee analysis.",
    "settings.data.title": "Premium Data Sources",
    "settings.data.subtitle": "Real-time tier — optional.",
    "settings.about.title": "About",
    "settings.active": "Active",
    "settings.demoMode": "demo mode (no key)",
    "settings.field.placeholder": "paste key…",
    "settings.field.placeholderHost": "http://localhost:11434",
    "settings.field.modelLabel": "Model",
    "settings.field.keyLabel": "API key",
    "settings.field.hostLabel": "Host URL",
    "settings.save": "Save",
    "settings.clear": "Clear",
    "settings.from.ui": "stored in UI",
    "settings.from.env": "loaded from .env",
    "settings.from.envModel": "model · from .env",
    "settings.from.uiModel": "model · custom",
    "settings.notSet": "not set",
    "settings.noKey": "Without a premium key, Argus uses yfinance + akshare (~15-min delayed for many feeds).",
    "settings.about.body":
      "Argus v{v} — open-source, MIT licensed. Multi-agent stock intelligence covering {markets}.",
    "settings.about.disclaimer":
      "This software is for research and education only. Nothing here is investment advice. Always do your own due diligence; past performance does not guarantee future results.",
    "settings.toolbar.theme": "Theme",
    "settings.toolbar.lang": "Language",

    // Smoke test
    "settings.test":              "Test",
    "settings.testing":           "Testing…",
    "settings.test.ok":           "Connected · {latency}ms",
    "settings.test.sample":       "model said: \"{sample}\"",
    "settings.test.kind.no_key":          "No key configured",
    "settings.test.kind.auth":            "Auth failed",
    "settings.test.kind.model_not_found": "Model not found",
    "settings.test.kind.rate_limit":      "Rate limited",
    "settings.test.kind.network":         "Network error",
    "settings.test.kind.timeout":         "Timeout",
    "settings.test.kind.unknown":         "Failed",

    // Error states
    "error.network":   "Network error — couldn't reach the Argus backend.",
    "error.upstream":  "Data source temporarily unavailable.",
    "error.validation":"Invalid request.",
    "error.unknown":   "Something went wrong.",
    "error.retry":     "Retry",

    // Sharing / export
    "share.copySummary": "Copy summary",
    "share.copied":      "Copied",
    "share.exportMarkdown": "Export full analysis",
    "share.shareLink":   "Copy link",
    "share.disclaimer":  "Argus is for research and education only. Not investment advice.",
    "share.export.thesis":             "Thesis",
    "share.export.analystCommentary":  "Analyst commentary",
    "share.export.agentFailed":        "This analyst's run failed mid-stream and was excluded from the synthesis.",
    "share.lowConviction":             "Low conviction — analysts disagree or signals are mixed. Treat this as one input, not a recommendation.",
    "watch.template":    "Download template",
    "watch.import":      "Import",
    "watch.importHint":  "Accepts the Argus JSON template, or a plain text file with one ticker per line.",
    "watch.imported":    "Imported {n} ticker(s).",
    "watch.importErr":   "Import failed — couldn't find any tickers in the file.",
  },

  zh: {
    "app.tagline": "多市场",

    // Sidebar
    "nav.dashboard": "首页",
    "nav.history": "历史分析",
    "nav.screener": "选股器",
    "nav.watchlist": "自选 · 提醒",
    "nav.settings": "设置",
    "sidebar.starGithub": "在 GitHub 点星",
    "sidebar.versionLine": "v0.1.0 · MIT 协议",

    // TopBar
    "topbar.live": "实时",
    "topbar.demo": "演示模式 · 请填 API Key",

    // SearchBar
    "search.placeholder": "搜任意股票代码 — AAPL · 600519 · 0700.HK · 腾讯 · 茅台",

    // Dashboard
    "dashboard.badge": "多智能体 · 多市场",
    "dashboard.alpha": "v0.1 alpha",
    "dashboard.heroLine1": "五位分析师，",
    "dashboard.heroLine2": "一只股票，",
    "dashboard.heroBrand": "Argus 给你答案。",
    "dashboard.heroDesc":
      "覆盖美股、A 股、港股的开源 AI 投资委员会。输入任意代码——五位分工不同的分析师 Agent 实时辩论，首席投资官（CIO）综合给出最终判断。",
    "dashboard.try": "试试：",
    "dashboard.cardDeep.title": "个股深读",
    "dashboard.cardDeep.tag": "单标的 · 完整报告",
    "dashboard.cardDeep.desc": "K线、技术指标、基本面、新闻——以及 AI 委员会的最终判断。",
    "dashboard.cardScreener.title": "跨市场选股",
    "dashboard.cardScreener.tag": "发现",
    "dashboard.cardScreener.desc": "用估值、动量、技术形态在美股 / A 股 / 港股之间联动筛选。",
    "dashboard.cardWatch.title": "自选 + 提醒",
    "dashboard.cardWatch.tag": "监控",
    "dashboard.cardWatch.desc": "添加自选股；当价格、涨跌幅或 RSI 跨过阈值时触发提醒。",
    "dashboard.snapshot": "实时快照",
    "dashboard.demoNotice":
      "未检测到 LLM API Key，委员会运行在演示模式。请在「设置」页填入 Key 或写入 .env，以启用真实分析。",

    // Stock page
    "stock.priceVolume": "价格 · 成交量",
    "stock.fundamentals": "基本面",
    "stock.news": "新闻",
    "stock.signals": "技术信号速读",
    "stock.noSignals": "暂无可用信号",
    "stock.businessSummary": "公司简介",
    "stock.noNews": "暂无新闻。",

    "stat.open": "开盘",
    "stat.high": "最高",
    "stat.low": "最低",
    "stat.prevClose": "昨收",
    "stat.volume": "成交量",
    "stat.marketCap": "总市值",
    "stat.peTrailing": "市盈率 TTM",
    "stat.peForward": "前瞻 PE",
    "stat.pb": "市净率",
    "stat.ps": "市销率",
    "stat.divYield": "股息率",
    "stat.epsTtm": "每股收益 TTM",
    "stat.profitMargin": "净利率",
    "stat.beta": "Beta",
    "stat.high52": "52 周高",
    "stat.low52": "52 周低",

    // Committee
    "comm.title": "AI 投资委员会",
    "comm.subtitle": "6 位分析师 Agent · CIO 综合裁定",
    "comm.deliberating": "讨论中",
    "comm.verdictReady": "结论已出",
    "comm.run": "开始分析",
    "comm.synthesis": "首席投资官 · 综合判断",
    "comm.entryZone": "建议入场区间",
    "comm.stopZone": "止损参考",
    "comm.keyRisks": "主要风险",
    "comm.horizon": "持有期",
    "comm.conviction": "置信度：",

    // Agents
    "agent.technical.name": "技术分析师",
    "agent.fundamental.name": "基本面分析师",
    "agent.sentiment.name": "情绪分析师",
    "agent.macro.name": "宏观策略师",
    "agent.risk.name": "风险经理",
    "agent.flow.name": "资金流分析师",
    "agent.cio.name": "首席投资官",
    "agent.status.thinking": "推理中…",
    "agent.status.done": "已完成",
    "agent.status.error": "出错",
    "agent.status.queued": "等待中",
    "agent.noOutput": "（模型返回了空内容——可重试或换 provider）",
    "agent.runFailed": "（这位分析师本次推理失败——详情见系统日志）",
    "agent.retry": "重试",

    // History page
    "history.title":         "历史分析",
    "history.subtitle":      "本地保存的最近 AI 委员会 verdict 记录。",
    "history.empty":         "暂无历史分析。",
    "history.emptyHint":     "随便分析一只股票，结论就会出现在这里。",
    "history.openStock":     "打开个股页",
    "history.remove":        "从历史中移除",
    "history.clearAll":      "清空全部",
    "history.clearConfirm":  "确定要清空所有历史分析吗？此操作不可撤销。",
    "history.lowConvHint":   "本次结论的置信度偏低。",

    // Screener
    "screener.title": "跨市场选股器",
    "screener.subtitle": "按形态扫描美股 · A 股 · 港股。（自定义条件即将上线。）",
    "screener.preset.momentum": "动量",
    "screener.preset.oversold": "超卖",
    "screener.preset.all": "全部市场",
    "screener.col.symbol": "代码",
    "screener.col.name": "名称",
    "screener.col.market": "市场",
    "screener.col.price": "价格",
    "screener.col.change": "涨跌 %",
    "screener.col.rsi": "RSI",
    "screener.col.mcap": "市值",
    "screener.empty": "无匹配结果。",

    // Watchlist
    "watch.title": "自选股",
    "watch.subtitle": "每 30 秒刷新一次实时报价。",
    "watch.add": "添加",
    "watch.placeholder": "输入代码 — 如 NVDA、600519、0700.HK",
    "watch.empty": "暂无自选股，可在上方添加。",
    "watch.alerts.title": "提醒规则",
    "watch.alerts.subtitle": "基于规则；可手动求值或交给 cron。",
    "watch.alerts.add": "新增提醒",
    "watch.alerts.evaluate": "立即求值",
    "watch.alerts.empty": "暂无提醒规则。",
    "watch.alerts.symbol": "代码",
    "watch.alerts.value": "阈值",
    "watch.alerts.metric.price": "价格",
    "watch.alerts.metric.changePct": "涨跌 %",
    "watch.alerts.metric.rsi": "RSI(14)",
    "watch.alerts.none": "本次未触发任何提醒。",
    "watch.alerts.triggered": "已触发 {n} 条。",

    // Settings
    "settings.llm.title": "LLM 服务商",
    "settings.llm.subtitle": "粘贴 API Key 即可启用真实的 AI 委员会分析。",
    "settings.data.title": "高级行情源",
    "settings.data.subtitle": "实时数据，可选。",
    "settings.about.title": "关于",
    "settings.active": "当前生效",
    "settings.demoMode": "演示模式（未配置 Key）",
    "settings.field.placeholder": "粘贴 Key…",
    "settings.field.placeholderHost": "http://localhost:11434",
    "settings.field.modelLabel": "型号",
    "settings.field.keyLabel": "API Key",
    "settings.field.hostLabel": "Host 地址",
    "settings.save": "保存",
    "settings.clear": "清除",
    "settings.from.ui": "存于本机",
    "settings.from.env": "来自 .env",
    "settings.from.envModel": "型号 · 来自 .env",
    "settings.from.uiModel": "型号 · 自定义",
    "settings.notSet": "未设置",
    "settings.noKey": "未配置高级行情源时，Argus 使用 yfinance + akshare（部分行情约 15 分钟延迟）。",
    "settings.about.body":
      "Argus v{v} — 开源软件，MIT 协议。覆盖 {markets} 的多智能体股票分析平台。",
    "settings.about.disclaimer":
      "本软件仅供研究与教育用途，不构成投资建议。请独立做尽职调查；过往业绩不预示未来表现。",
    "settings.toolbar.theme": "主题",
    "settings.toolbar.lang": "语言",

    // Smoke test
    "settings.test":              "测试",
    "settings.testing":           "测试中…",
    "settings.test.ok":           "连通 · {latency}ms",
    "settings.test.sample":       "模型回复：\"{sample}\"",
    "settings.test.kind.no_key":          "未配置 Key",
    "settings.test.kind.auth":            "认证失败",
    "settings.test.kind.model_not_found": "找不到该模型",
    "settings.test.kind.rate_limit":      "触发限流",
    "settings.test.kind.network":         "网络错误",
    "settings.test.kind.timeout":         "超时",
    "settings.test.kind.unknown":         "失败",

    // Error states
    "error.network":   "网络错误——无法连接到 Argus 后端。",
    "error.upstream":  "数据源暂不可用，请稍后重试。",
    "error.validation":"请求参数不合法。",
    "error.unknown":   "出错了。",
    "error.retry":     "重试",

    // Sharing / export
    "share.copySummary": "复制摘要",
    "share.copied":      "已复制",
    "share.exportMarkdown": "导出完整分析",
    "share.shareLink":   "复制链接",
    "share.disclaimer":  "本内容由 Argus 生成，仅供研究与教育用途，不构成投资建议。",
    "share.export.thesis":             "投资逻辑",
    "share.export.analystCommentary":  "分析师评论",
    "share.export.agentFailed":        "该分析师本次推理中断，未参与综合判断。",
    "share.lowConviction":             "置信度偏低——分析师观点存在分歧或信号混合，请将本结论视为参考之一，而非投资建议。",
    "watch.template":    "下载模板",
    "watch.import":      "导入",
    "watch.importHint":  "支持 Argus JSON 模板，或纯文本（每行一个代码）。",
    "watch.imported":    "已导入 {n} 只标的。",
    "watch.importErr":   "导入失败——文件中找不到合法代码。",
  },
};

interface Ctx {
  lang: Lang;
  setLang: (l: Lang) => void;
  toggle: () => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
}

const I18nCtx = createContext<Ctx | null>(null);
const STORAGE_KEY = "argus.lang";

function readInitial(): Lang {
  if (typeof window === "undefined") return "en";
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "en" || saved === "zh") return saved;
  const navL = (navigator.language || "en").toLowerCase();
  return navL.startsWith("zh") ? "zh" : "en";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(readInitial);

  useEffect(() => {
    document.documentElement.setAttribute("lang", lang);
    localStorage.setItem(STORAGE_KEY, lang);
  }, [lang]);

  const setLang = useCallback((l: Lang) => setLangState(l), []);
  const toggle = useCallback(() => setLangState((l) => (l === "en" ? "zh" : "en")), []);

  const t = useCallback(
    (key: string, vars?: Record<string, string | number>) => {
      const dict = DICT[lang] ?? DICT.en;
      let s = dict[key] ?? DICT.en[key] ?? key;
      if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
      return s;
    },
    [lang]
  );

  const value = useMemo(() => ({ lang, setLang, toggle, t }), [lang, setLang, toggle, t]);
  return <I18nCtx.Provider value={value}>{children}</I18nCtx.Provider>;
}

export function useI18n(): Ctx {
  const ctx = useContext(I18nCtx);
  if (!ctx) throw new Error("useI18n must be inside I18nProvider");
  return ctx;
}

export function useT() {
  return useI18n().t;
}
