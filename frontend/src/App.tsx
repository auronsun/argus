import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { Spinner } from "@/components/ui/Spinner";
import { Dashboard } from "@/pages/Dashboard";

const StockPage = lazy(() => import("@/pages/Stock").then((m) => ({ default: m.StockPage })));
const Screener  = lazy(() => import("@/pages/Screener").then((m) => ({ default: m.Screener })));
const Watchlist = lazy(() => import("@/pages/Watchlist").then((m) => ({ default: m.Watchlist })));
const HistoryP  = lazy(() => import("@/pages/History").then((m) => ({ default: m.History })));
const SettingsP = lazy(() => import("@/pages/Settings").then((m) => ({ default: m.Settings })));

function PageFallback() {
  return (
    <div className="h-full grid place-items-center text-zinc-500">
      <Spinner />
    </div>
  );
}

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto">
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/stock/:symbol" element={<StockPage />} />
              <Route path="/screener" element={<Screener />} />
              <Route path="/watchlist" element={<Watchlist />} />
              <Route path="/history" element={<HistoryP />} />
              <Route path="/settings" element={<SettingsP />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  );
}
