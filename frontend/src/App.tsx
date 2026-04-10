import { NavLink, Route, Routes } from "react-router-dom";
import { Activity, BarChart3, Bell, Grid3x3, LineChart, LogOut, Newspaper, Wallet } from "lucide-react";
import WatchlistPage from "./pages/WatchlistPage";
import ChartsPage from "./pages/ChartsPage";
import HeatmapPage from "./pages/HeatmapPage";
import AlertsPage from "./pages/AlertsPage";
import PaperTradingPage from "./pages/PaperTradingPage";
import NewsPage from "./pages/NewsPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import RequireAuth from "./components/RequireAuth";
import { useAuthStore } from "./stores/authStore";

const navItems = [
  { to: "/", label: "Watchlist", icon: LineChart, end: true },
  { to: "/chart/AAPL", label: "Charts", icon: BarChart3, end: false },
  { to: "/heatmap", label: "Heatmap", icon: Grid3x3, end: false },
  { to: "/alerts", label: "Alerts", icon: Bell, end: false },
  { to: "/paper", label: "Paper", icon: Wallet, end: false },
  { to: "/news", label: "News", icon: Newspaper, end: false },
];

function AppShell() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <div className="flex h-full w-full">
      <aside className="flex w-56 shrink-0 flex-col border-r border-zinc-800 bg-zinc-900/60 p-4">
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
        <div className="mt-auto flex flex-col gap-2 border-t border-zinc-800 pt-4 text-sm">
          {user && (
            <div className="truncate text-xs text-zinc-400" title={user.email}>
              {user.email}
            </div>
          )}
          <button
            onClick={logout}
            className="flex items-center gap-2 rounded px-3 py-2 text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-100"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
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

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="*"
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      />
    </Routes>
  );
}
