import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDownRight,
  ArrowUpRight,
  DollarSign,
  PieChart,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { paperApi, type Portfolio, type Trade } from "../api/paper";
import { useTickerStream } from "../hooks/useTickerStream";
import { useTickerStore } from "../stores/tickerStore";
import { formatPrice, formatPct, pctClass } from "../lib/format";
import TradeModal from "../components/TradeModal";

/* ─── Stat Card ─────────────────────────────────────────────────── */
function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ElementType;
  accent?: string;
}) {
  return (
    <div className="stat-card animate-fade-in">
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
        <Icon className={`h-4 w-4 ${accent ?? "text-zinc-500"}`} />
        {label}
      </div>
      <div className="mt-1 text-xl font-semibold font-mono text-zinc-100">{value}</div>
      {sub && <div className={`mt-0.5 text-xs font-mono ${accent ?? "text-zinc-500"}`}>{sub}</div>}
    </div>
  );
}

/* ─── Main Page ─────────────────────────────────────────────────── */
export default function PaperTradingPage() {
  const qc = useQueryClient();

  /* ── form state ── */
  /* ── form state ── */
  // Removed unused simple form state

  /* ── modal state ── */
  const [modalOpen, setModalOpen] = useState(false);
  const [modalSide, setModalSide] = useState<"buy" | "sell" | null>(null);

  /* ── queries ── */
  const portfolioQ = useQuery<Portfolio>({
    queryKey: ["paper", "portfolio"],
    queryFn: paperApi.portfolio,
    refetchInterval: 15_000,
  });

  const tradesQ = useQuery<Trade[]>({
    queryKey: ["paper", "trades"],
    queryFn: paperApi.trades,
  });

  /* ── live price stream for positions ── */
  const positionSymbols = useMemo(
    () => portfolioQ.data?.positions.map((p) => p.symbol) ?? [],
    [portfolioQ.data],
  );
  useTickerStream(positionSymbols);
  const ticks = useTickerStore((s) => s.ticks);

  /* ── mutations ── */
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["paper"] });
  };

  const openTradeModal = (side: "buy" | "sell" | null) => {
    setModalSide(side);
    setModalOpen(true);
  };

  /* ── derived data ── */
  const portfolio = portfolioQ.data;
  const totalPnl = portfolio
    ? portfolio.total_value - portfolio.initial_cash
    : null;
  const totalPnlPct = portfolio && portfolio.initial_cash > 0
    ? ((portfolio.total_value - portfolio.initial_cash) / portfolio.initial_cash) * 100
    : null;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-zinc-100">Paper Trading</h1>
        {portfolio && (
          <span className="rounded bg-zinc-800 px-2.5 py-1 text-xs font-mono text-zinc-400">
            Starting Capital: {formatPrice(portfolio.initial_cash)}
          </span>
        )}
      </div>

      {/* ── Portfolio Summary ── */}
      {portfolioQ.isLoading && (
        <div className="grid grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton h-20 rounded-lg" />
          ))}
        </div>
      )}
      {portfolio && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            label="Total Value"
            value={formatPrice(portfolio.total_value)}
            sub={totalPnl !== null ? `${totalPnl >= 0 ? "+" : ""}${formatPrice(totalPnl)}` : undefined}
            icon={TrendingUp}
            accent={totalPnl !== null ? (totalPnl >= 0 ? "text-emerald-400" : "text-rose-400") : undefined}
          />
          <StatCard
            label="Cash"
            value={formatPrice(portfolio.cash)}
            icon={DollarSign}
          />
          <StatCard
            label="Market Value"
            value={formatPrice(portfolio.market_value)}
            icon={PieChart}
            accent="text-sky-400"
          />
          <StatCard
            label="Total P&L"
            value={totalPnlPct !== null ? formatPct(totalPnlPct) : "—"}
            sub={totalPnl !== null ? formatPrice(Math.abs(totalPnl)) : undefined}
            icon={Wallet}
            accent={totalPnlPct !== null ? (totalPnlPct >= 0 ? "text-emerald-400" : "text-rose-400") : undefined}
          />
        </div>
      )}

      {/* ── Order Form ── */}
      <div className="flex gap-4">
        <button
          onClick={() => openTradeModal("buy")}
          className="flex-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-4 text-emerald-400 font-semibold transition-colors hover:bg-emerald-500/20 flex items-center justify-center gap-2"
        >
          <ArrowUpRight className="h-5 w-5" />
          Buy Stock
        </button>
        <button
          onClick={() => openTradeModal("sell")}
          className="flex-1 rounded-lg bg-rose-500/10 border border-rose-500/20 px-4 py-4 text-rose-400 font-semibold transition-colors hover:bg-rose-500/20 flex items-center justify-center gap-2"
        >
          <ArrowDownRight className="h-5 w-5" />
          Sell Stock
        </button>
      </div>

      {/* ── Positions Table ── */}
      <div className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
          Positions
        </h2>
        {portfolio && portfolio.positions.length === 0 && (
          <div className="card p-6 text-center text-sm text-zinc-500">
            No open positions. Place a buy order above to get started.
          </div>
        )}
        {portfolio && portfolio.positions.length > 0 && (
          <div className="overflow-x-auto rounded border border-zinc-800">
            <table className="w-full border-collapse text-sm">
              <thead className="bg-zinc-900/80 text-left text-xs uppercase tracking-wide text-zinc-500">
                <tr>
                  <th className="px-4 py-2.5">Symbol</th>
                  <th className="px-4 py-2.5 text-right">Qty</th>
                  <th className="px-4 py-2.5 text-right">Avg Cost</th>
                  <th className="px-4 py-2.5 text-right">Last Price</th>
                  <th className="px-4 py-2.5 text-right">Mkt Value</th>
                  <th className="px-4 py-2.5 text-right">P&L</th>
                  <th className="px-4 py-2.5 text-right">P&L %</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((pos) => {
                  const live = ticks[pos.symbol]?.price ?? pos.last_price;
                  const mv = live !== null && live !== undefined ? live * pos.quantity : pos.market_value;
                  const pnl = live !== null && live !== undefined
                    ? (live - pos.avg_cost) * pos.quantity
                    : pos.unrealized_pnl;
                  const pnlPct = live !== null && live !== undefined && pos.avg_cost > 0
                    ? ((live - pos.avg_cost) / pos.avg_cost) * 100
                    : pos.unrealized_pnl_pct;

                  return (
                    <tr
                      key={pos.symbol}
                      className="border-t border-zinc-800/60 transition-colors hover:bg-zinc-800/30"
                    >
                      <td className="px-4 py-2.5 font-mono font-semibold text-zinc-100">
                        {pos.symbol}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono">{pos.quantity}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{formatPrice(pos.avg_cost)}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-zinc-200">
                        {formatPrice(live)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono">
                        {formatPrice(mv)}
                      </td>
                      <td className={`px-4 py-2.5 text-right font-mono font-medium ${pctClass(pnl)}`}>
                        {pnl !== null && pnl !== undefined
                          ? `${pnl >= 0 ? "+" : ""}${formatPrice(pnl)}`
                          : "—"}
                      </td>
                      <td className={`px-4 py-2.5 text-right font-mono font-medium ${pctClass(pnlPct)}`}>
                        {formatPct(pnlPct)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Trade History ── */}
      <div className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
          Trade History
        </h2>
        {tradesQ.isLoading && <div className="skeleton h-16 rounded-lg" />}
        {tradesQ.data && tradesQ.data.length === 0 && (
          <div className="card p-6 text-center text-sm text-zinc-500">
            No trades yet.
          </div>
        )}
        {tradesQ.data && tradesQ.data.length > 0 && (
          <div className="max-h-72 overflow-y-auto rounded border border-zinc-800">
            <table className="w-full border-collapse text-sm">
              <thead className="sticky top-0 bg-zinc-900/95 text-left text-xs uppercase tracking-wide text-zinc-500 backdrop-blur">
                <tr>
                  <th className="px-4 py-2">Side</th>
                  <th className="px-4 py-2">Symbol</th>
                  <th className="px-4 py-2 text-right">Qty</th>
                  <th className="px-4 py-2 text-right">Price</th>
                  <th className="px-4 py-2 text-right">Total</th>
                  <th className="px-4 py-2 text-right">Time</th>
                </tr>
              </thead>
              <tbody>
                {tradesQ.data.map((t) => (
                  <tr
                    key={t.id}
                    className="border-t border-zinc-800/60 transition-colors hover:bg-zinc-800/30"
                  >
                    <td className="px-4 py-2">
                      <span
                        className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-bold uppercase ${
                          t.side === "buy"
                            ? "bg-emerald-500/15 text-emerald-400"
                            : "bg-rose-500/15 text-rose-400"
                        }`}
                      >
                        {t.side}
                      </span>
                    </td>
                    <td className="px-4 py-2 font-mono font-semibold text-zinc-200">{t.symbol}</td>
                    <td className="px-4 py-2 text-right font-mono">{t.quantity}</td>
                    <td className="px-4 py-2 text-right font-mono">{formatPrice(t.price)}</td>
                    <td className="px-4 py-2 text-right font-mono text-zinc-300">
                      {formatPrice(t.price * t.quantity)}
                    </td>
                    <td className="px-4 py-2 text-right text-xs text-zinc-500">
                      {new Date(t.executed_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <TradeModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        initialSide={modalSide}
        portfolio={portfolio}
        onSuccess={invalidate}
      />
    </div>
  );
}
