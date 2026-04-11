import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDownRight,
  ArrowUpRight,
  Clock,
  DollarSign,
  PieChart,
  RotateCcw,
  TrendingUp,
  Wallet,
  X,
  Zap,
} from "lucide-react";
import { paperApi, type LimitOrder, type Portfolio, type Trade } from "../api/paper";
import { useTickerStream } from "../hooks/useTickerStream";
import { useTickerStore } from "../stores/tickerStore";
import { formatPrice, formatPct, pctClass } from "../lib/format";
import { useMarketStatus, sessionLabel } from "../hooks/useMarketStatus";
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

/* ─── Market Status Pill ────────────────────────────────────────── */
function MarketStatusPill() {
  const { data } = useMarketStatus();
  if (!data) return null;
  const open = data.open;
  const label = sessionLabel(data.session);
  const color = open
    ? data.session === "regular"
      ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
      : "bg-amber-500/15 text-amber-400 border-amber-500/30"
    : "bg-zinc-800 text-zinc-400 border-zinc-700";
  const dot = open
    ? data.session === "regular"
      ? "bg-emerald-400"
      : "bg-amber-400"
    : "bg-zinc-500";
  const tooltip = open
    ? `Trading allowed (${label})`
    : `Closed — opens ${new Date(data.next_open_iso).toLocaleString()}`;
  return (
    <span
      title={tooltip}
      className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-medium ${color}`}
    >
      <span className={`h-1.5 w-1.5 animate-pulse rounded-full ${dot}`} />
      {label}
    </span>
  );
}

/* ─── Reset Confirm Modal ───────────────────────────────────────── */
function ResetConfirmModal({
  open,
  onClose,
  onConfirm,
  pending,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  pending: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-sm overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl">
        <div className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/50 p-4">
          <h2 className="text-lg font-semibold text-zinc-100">Reset Portfolio</h2>
          <button onClick={onClose} className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-4 p-6 text-sm text-zinc-300">
          <p>This will permanently delete all positions, trades, open limit orders, and pending settlements, and reset cash to <span className="font-mono">$100,000</span>.</p>
          <p className="text-rose-400">This cannot be undone.</p>
          <div className="flex gap-3 pt-2">
            <button
              onClick={onClose}
              disabled={pending}
              className="flex-1 rounded border border-zinc-800 bg-zinc-900 py-2.5 font-medium text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={pending}
              className="flex-1 rounded bg-rose-500 py-2.5 font-semibold text-zinc-950 hover:bg-rose-400 disabled:opacity-50"
            >
              {pending ? "Resetting..." : "Reset"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function pendingCountdown(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "settled";
  const mins = Math.ceil(ms / 60_000);
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

/* ─── Main Page ─────────────────────────────────────────────────── */
export default function PaperTradingPage() {
  const qc = useQueryClient();

  const [modalOpen, setModalOpen] = useState(false);
  const [modalSide, setModalSide] = useState<"buy" | "sell" | null>(null);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetPending, setResetPending] = useState(false);

  const portfolioQ = useQuery<Portfolio>({
    queryKey: ["paper", "portfolio"],
    queryFn: paperApi.portfolio,
    refetchInterval: 15_000,
  });

  const tradesQ = useQuery<Trade[]>({
    queryKey: ["paper", "trades"],
    queryFn: paperApi.trades,
  });

  const ordersQ = useQuery<LimitOrder[]>({
    queryKey: ["paper", "orders"],
    queryFn: paperApi.listOrders,
    refetchInterval: 10_000,
  });

  const marketQ = useMarketStatus();
  const marketOpen = marketQ.data?.open ?? false;

  /* ── live price stream for positions + open orders ── */
  const liveSymbols = useMemo(() => {
    const s = new Set<string>();
    portfolioQ.data?.positions.forEach((p) => s.add(p.symbol));
    ordersQ.data?.forEach((o) => s.add(o.symbol));
    return Array.from(s);
  }, [portfolioQ.data, ordersQ.data]);
  useTickerStream(liveSymbols);
  const ticks = useTickerStore((s) => s.ticks);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["paper"] });
  };

  const openTradeModal = (side: "buy" | "sell" | null) => {
    setModalSide(side);
    setModalOpen(true);
  };

  const handleReset = async () => {
    setResetPending(true);
    try {
      await paperApi.reset();
      invalidate();
      setResetOpen(false);
    } catch (err) {
      console.error(err);
    } finally {
      setResetPending(false);
    }
  };

  const handleCancelOrder = async (id: number) => {
    try {
      await paperApi.cancelOrder(id);
      invalidate();
    } catch (err) {
      console.error(err);
    }
  };

  const portfolio = portfolioQ.data;
  const totalPnl = portfolio ? portfolio.total_value - portfolio.initial_cash : null;
  const totalPnlPct =
    portfolio && portfolio.initial_cash > 0
      ? ((portfolio.total_value - portfolio.initial_cash) / portfolio.initial_cash) * 100
      : null;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Header ── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold text-zinc-100">Paper Trading</h1>
          <MarketStatusPill />
        </div>
        <div className="flex items-center gap-2">
          {portfolio && (
            <span className="rounded bg-zinc-800 px-2.5 py-1 text-xs font-mono text-zinc-400">
              Starting Capital: {formatPrice(portfolio.initial_cash)}
            </span>
          )}
          <button
            onClick={() => setResetOpen(true)}
            className="inline-flex items-center gap-1.5 rounded border border-zinc-800 bg-zinc-900 px-3 py-1 text-xs font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset
          </button>
        </div>
      </div>

      {/* ── Portfolio Summary ── */}
      {portfolioQ.isLoading && (
        <div className="grid grid-cols-3 gap-3 lg:grid-cols-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="skeleton h-20 rounded-lg" />
          ))}
        </div>
      )}
      {portfolio && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
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
            sub={
              portfolio.pending_settlement > 0
                ? `${formatPrice(portfolio.pending_settlement)} settling`
                : undefined
            }
            icon={DollarSign}
            accent={portfolio.pending_settlement > 0 ? "text-amber-400" : undefined}
          />
          <StatCard
            label="Buying Power"
            value={formatPrice(portfolio.buying_power)}
            sub={
              portfolio.reserved_for_orders > 0
                ? `${formatPrice(portfolio.reserved_for_orders)} reserved`
                : undefined
            }
            icon={Zap}
            accent="text-amber-400"
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
          <StatCard
            label="Realized P&L"
            value={`${portfolio.realized_pnl >= 0 ? "+" : ""}${formatPrice(portfolio.realized_pnl)}`}
            icon={TrendingUp}
            accent={portfolio.realized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}
          />
        </div>
      )}

      {/* ── Pending Settlements Detail ── */}
      {portfolio && portfolio.pending_settlements.length > 0 && (
        <div className="rounded border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-200">
          <div className="mb-1 flex items-center gap-1.5 font-semibold uppercase tracking-wide">
            <Clock className="h-3.5 w-3.5" />
            Pending Settlements
          </div>
          <ul className="space-y-0.5 font-mono">
            {portfolio.pending_settlements.map((s, i) => (
              <li key={i} className="flex justify-between">
                <span>{formatPrice(s.amount)}</span>
                <span className="text-amber-400">settles in {pendingCountdown(s.settles_at)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Order Form Buttons ── */}
      <div className="flex gap-4">
        <button
          onClick={() => openTradeModal("buy")}
          title={marketOpen ? undefined : "Market is closed — only limit orders can be placed"}
          className="flex-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-4 text-emerald-400 font-semibold transition-colors hover:bg-emerald-500/20 flex items-center justify-center gap-2"
        >
          <ArrowUpRight className="h-5 w-5" />
          Buy Stock
        </button>
        <button
          onClick={() => openTradeModal("sell")}
          title={marketOpen ? undefined : "Market is closed — only limit orders can be placed"}
          className="flex-1 rounded-lg bg-rose-500/10 border border-rose-500/20 px-4 py-4 text-rose-400 font-semibold transition-colors hover:bg-rose-500/20 flex items-center justify-center gap-2"
        >
          <ArrowDownRight className="h-5 w-5" />
          Sell Stock
        </button>
      </div>

      {!marketOpen && marketQ.data && (
        <div className="rounded border border-zinc-800 bg-zinc-900/40 px-4 py-2 text-center text-xs text-zinc-500">
          Market closed — only limit orders can be placed. Next session opens{" "}
          <span className="font-mono text-zinc-300">
            {new Date(marketQ.data.next_open_iso).toLocaleString()}
          </span>
          .
        </div>
      )}

      {/* ── Positions Table ── */}
      <div className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Positions</h2>
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
                  <th className="px-4 py-2.5 text-right">Last</th>
                  <th className="px-4 py-2.5 text-right">Day $</th>
                  <th className="px-4 py-2.5 text-right">Day %</th>
                  <th className="px-4 py-2.5 text-right">Mkt Value</th>
                  <th className="px-4 py-2.5 text-right">P&L</th>
                  <th className="px-4 py-2.5 text-right">P&L %</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((pos) => {
                  const live = ticks[pos.symbol]?.price ?? pos.last_price;
                  const mv = live !== null && live !== undefined ? live * pos.quantity : pos.market_value;
                  const pnl =
                    live !== null && live !== undefined
                      ? (live - pos.avg_cost) * pos.quantity
                      : pos.unrealized_pnl;
                  const pnlPct =
                    live !== null && live !== undefined && pos.avg_cost > 0
                      ? ((live - pos.avg_cost) / pos.avg_cost) * 100
                      : pos.unrealized_pnl_pct;
                  // Day change recomputed live if we have prev_close
                  const dayChange =
                    live !== null && live !== undefined && pos.prev_close && pos.prev_close > 0
                      ? (live - pos.prev_close) * pos.quantity
                      : pos.day_change;
                  const dayChangePct =
                    live !== null && live !== undefined && pos.prev_close && pos.prev_close > 0
                      ? ((live - pos.prev_close) / pos.prev_close) * 100
                      : pos.day_change_pct;

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
                      <td className="px-4 py-2.5 text-right font-mono text-zinc-200">{formatPrice(live)}</td>
                      <td className={`px-4 py-2.5 text-right font-mono ${pctClass(dayChange)}`}>
                        {dayChange !== null && dayChange !== undefined
                          ? `${dayChange >= 0 ? "+" : ""}${formatPrice(dayChange)}`
                          : "—"}
                      </td>
                      <td className={`px-4 py-2.5 text-right font-mono ${pctClass(dayChangePct)}`}>
                        {formatPct(dayChangePct)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono">{formatPrice(mv)}</td>
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

      {/* ── Open Limit Orders ── */}
      {ordersQ.data && ordersQ.data.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Open Orders</h2>
          <div className="overflow-x-auto rounded border border-zinc-800">
            <table className="w-full border-collapse text-sm">
              <thead className="bg-zinc-900/80 text-left text-xs uppercase tracking-wide text-zinc-500">
                <tr>
                  <th className="px-4 py-2.5">Side</th>
                  <th className="px-4 py-2.5">Symbol</th>
                  <th className="px-4 py-2.5 text-right">Qty</th>
                  <th className="px-4 py-2.5 text-right">Limit</th>
                  <th className="px-4 py-2.5 text-right">Last</th>
                  <th className="px-4 py-2.5 text-right">Placed</th>
                  <th className="px-4 py-2.5 text-right"></th>
                </tr>
              </thead>
              <tbody>
                {ordersQ.data.map((o) => {
                  const live = ticks[o.symbol]?.price;
                  return (
                    <tr key={o.id} className="border-t border-zinc-800/60 hover:bg-zinc-800/30">
                      <td className="px-4 py-2.5">
                        <span
                          className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-bold uppercase ${
                            o.side === "buy"
                              ? "bg-emerald-500/15 text-emerald-400"
                              : "bg-rose-500/15 text-rose-400"
                          }`}
                        >
                          {o.side}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 font-mono font-semibold text-zinc-200">{o.symbol}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{o.quantity}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-zinc-200">
                        {formatPrice(o.limit_price)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-zinc-400">
                        {formatPrice(live ?? null)}
                      </td>
                      <td className="px-4 py-2.5 text-right text-xs text-zinc-500">
                        {new Date(o.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <button
                          onClick={() => handleCancelOrder(o.id)}
                          className="rounded bg-zinc-800 px-2 py-1 text-xs text-zinc-300 hover:bg-rose-500/20 hover:text-rose-300"
                        >
                          Cancel
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Trade History ── */}
      <div className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Trade History</h2>
        {tradesQ.isLoading && <div className="skeleton h-16 rounded-lg" />}
        {tradesQ.data && tradesQ.data.length === 0 && (
          <div className="card p-6 text-center text-sm text-zinc-500">No trades yet.</div>
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
                  <th className="px-4 py-2 text-right">Realized</th>
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
                    <td className={`px-4 py-2 text-right font-mono ${pctClass(t.realized_pnl)}`}>
                      {t.realized_pnl !== null && t.realized_pnl !== undefined
                        ? `${t.realized_pnl >= 0 ? "+" : ""}${formatPrice(t.realized_pnl)}`
                        : "—"}
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
        marketOpen={marketOpen}
        onSuccess={invalidate}
      />

      <ResetConfirmModal
        open={resetOpen}
        onClose={() => setResetOpen(false)}
        onConfirm={handleReset}
        pending={resetPending}
      />
    </div>
  );
}
