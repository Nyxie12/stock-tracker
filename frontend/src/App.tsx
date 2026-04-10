import { NavLink, Route, Routes } from "react-router-dom";
import { Activity, BarChart3, Bell, Grid3x3, LineChart, Newspaper, Wallet } from "lucide-react";
import WatchlistPage from "./pages/WatchlistPage";
import ChartsPage from "./pages/ChartsPage";
import HeatmapPage from "./pages/HeatmapPage";
import AlertsPage from "./pages/AlertsPage";
import PaperTradingPage from "./pages/PaperTradingPage";
import NewsPage from "./pages/NewsPage";

const navItems = [
  { to: "/", label: "Watchlist", icon: LineChart, end: true },
  { to: "/chart/AAPL", label: "Charts", icon: BarChart3, end: false },
  { to: "/heatmap", label: "Heatmap", icon: Grid3x3, end: false },
  { to: "/alerts", label: "Alerts", icon: Bell, end: false },
  { to: "/paper", label: "Paper", icon: Wallet, end: false },
  { to: "/news", label: "News", icon: Newspaper, end: false },
];

export default function App() {
  return (
    <div className="flex h-full w-full">
      <aside className="w-56 shrink-0 border-r border-zinc-800 bg-zinc-900/60 p-4">
        <div className="mb-6 flex items-center gap-2 text-lg font-semibold">
          <Activity className="h-5 w-5 text-emerald-400" />
          <span>Stock Tracker</span>
        </div>
        <nav className="flex flex-col gap-1">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-100"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Routes>
          <Route path="/" element={<WatchlistPage />} />
          <Route path="/chart/:symbol" element={<ChartsPage />} />
          <Route path="/heatmap" element={<HeatmapPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/paper" element={<PaperTradingPage />} />
          <Route path="/news" element={<NewsPage />} />
          <Route path="/news/:symbol" element={<NewsPage />} />
        </Routes>
      </main>
    </div>
  );
}
