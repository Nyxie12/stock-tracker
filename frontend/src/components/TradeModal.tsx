import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { X, Search } from "lucide-react";
import { paperApi, type Portfolio } from "../api/paper";
import { quoteApi } from "../api/quote";
import { formatPrice } from "../lib/format";
import { useTickerStream } from "../hooks/useTickerStream";
import { useTickerStore } from "../stores/tickerStore";

type Mode = "shares" | "dollars";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  initialSide: "buy" | "sell" | null;
  portfolio: Portfolio | undefined;
  onSuccess: () => void;
};

export default function TradeModal({ isOpen, onClose, initialSide, portfolio, onSuccess }: Props) {
  const [side, setSide] = useState<"buy" | "sell">(initialSide || "buy");
  const [mode, setMode] = useState<Mode>("shares");
  const [symbolInput, setSymbolInput] = useState("");
  const [activeSymbol, setActiveSymbol] = useState("");
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState<"select_side" | "input" | "confirm">(initialSide ? "input" : "select_side");

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setSide(initialSide || "buy");
      setMode("shares");
      setSymbolInput("");
      setActiveSymbol("");
      setAmount("");
      setError(null);
      setSubmitting(false);
      setStep(initialSide ? "input" : "select_side");
    }
  }, [isOpen, initialSide]);

  // Subscribe to live ticks for the active symbol
  useTickerStream(activeSymbol ? [activeSymbol] : []);
  const liveTick = useTickerStore((s) => s.ticks[activeSymbol]?.price);

  // Fetch REST quote in case tick stream is slow or empty
  const quoteQ = useQuery({
    queryKey: ["quote", activeSymbol],
    queryFn: () => quoteApi.get(activeSymbol),
    enabled: activeSymbol.length > 0,
    retry: false,
  });

  const price = liveTick ?? quoteQ.data?.c ?? null;

  // Derived calculations
  const parsedAmount = parseFloat(amount) || 0;
  
  let shares = 0;
  let costOrProceeds = 0;

  if (price && price > 0) {
    if (mode === "shares") {
      shares = Math.floor(parsedAmount);
      costOrProceeds = shares * price;
    } else {
      shares = Math.floor(parsedAmount / price);
      costOrProceeds = shares * price;
    }
  }

  // Find existing position for selling
  const position = portfolio?.positions.find((p) => p.symbol === activeSymbol);

  const handleSymbolSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const s = symbolInput.trim().toUpperCase();
    if (s) {
      setActiveSymbol(s);
      setError(null);
    }
  };

  const handleConfirmReview = () => {
    setError(null);
    if (!activeSymbol) {
      setError("Please select a symbol.");
      return;
    }
    if (!price || price <= 0) {
      setError("Cannot fetch live price for this symbol.");
      return;
    }
    if (shares <= 0) {
      setError(`Amount too small to buy at least 1 share (Price: ${formatPrice(price)}).`);
      return;
    }
    if (side === "buy" && portfolio) {
      if (costOrProceeds > portfolio.cash) {
        setError(`Insufficient cash. Need ${formatPrice(costOrProceeds)}, have ${formatPrice(portfolio.cash)}`);
        return;
      }
    }
    if (side === "sell") {
      if (!position || position.quantity < shares) {
        setError(`Insufficient shares. You only own ${position?.quantity || 0} shares.`);
        return;
      }
    }
    setStep("confirm");
  };

  const executeTrade = async () => {
    setSubmitting(true);
    setError(null);
    try {
      if (side === "buy") {
        await paperApi.buy(activeSymbol, shares);
      } else {
        await paperApi.sell(activeSymbol, shares);
      }
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to execute trade.");
      setStep("input");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/50 p-4">
          <h2 className="text-lg font-semibold text-zinc-100">
            {step === "select_side" ? "New Trade" : side === "buy" ? "Buy Stock" : "Sell Stock"}
          </h2>
          <button
            onClick={onClose}
            className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6">
          {step === "select_side" && (
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => {
                  setSide("buy");
                  setStep("input");
                }}
                className="flex flex-col items-center justify-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 p-6 transition-colors hover:border-emerald-500 hover:bg-emerald-500/10"
              >
                <div className="rounded-full bg-emerald-500/20 p-3 text-emerald-400">
                  <span className="text-xl font-bold">Buy</span>
                </div>
                <span className="text-sm text-zinc-400">Purchase shares</span>
              </button>
              <button
                onClick={() => {
                  setSide("sell");
                  setStep("input");
                }}
                className="flex flex-col items-center justify-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 p-6 transition-colors hover:border-rose-500 hover:bg-rose-500/10"
              >
                <div className="rounded-full bg-rose-500/20 p-3 text-rose-400">
                  <span className="text-xl font-bold">Sell</span>
                </div>
                <span className="text-sm text-zinc-400">Liquidate positions</span>
              </button>
            </div>
          )}

          {step === "input" && (
            <div className="space-y-6 animate-fade-in">
              {/* Symbol Input */}
              <div className="space-y-2">
                <label className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                  {side === "buy" ? "Symbol" : "Position to Sell"}
                </label>
                {side === "buy" ? (
                  <form onSubmit={handleSymbolSearch} className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                    <input
                      value={symbolInput}
                      onChange={(e) => setSymbolInput(e.target.value.toUpperCase())}
                      onBlur={handleSymbolSearch}
                      placeholder="AAPL"
                      className="w-full rounded border border-zinc-800 bg-zinc-900 py-2.5 pl-9 pr-4 font-mono text-zinc-100 placeholder:text-zinc-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                    />
                  </form>
                ) : (
                  <select
                    value={activeSymbol}
                    onChange={(e) => setActiveSymbol(e.target.value)}
                    className="w-full appearance-none rounded border border-zinc-800 bg-zinc-900 p-2.5 font-mono text-zinc-100 focus:border-rose-500 focus:outline-none"
                  >
                    <option value="">Select a position...</option>
                    {portfolio?.positions.map((p) => (
                      <option key={p.symbol} value={p.symbol}>
                        {p.symbol} ({p.quantity} shares)
                      </option>
                    ))}
                  </select>
                )}

                {activeSymbol && (
                  <div className="flex items-center justify-between rounded bg-zinc-900 px-3 py-2 text-sm">
                    <span className="font-mono font-medium text-zinc-300">{activeSymbol}</span>
                    {quoteQ.isLoading && !liveTick ? (
                      <span className="text-xs text-zinc-500">Fetching price...</span>
                    ) : price ? (
                      <span className="font-mono text-zinc-100">{formatPrice(price)}</span>
                    ) : (
                      <span className="text-xs text-rose-400">Unable to quote</span>
                    )}
                  </div>
                )}
              </div>

              {/* Amount Input */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium uppercase tracking-wide text-zinc-500">Amount</label>
                  <div className="inline-flex overflow-hidden rounded border border-zinc-800 bg-zinc-900">
                    <button
                      onClick={() => { setMode("shares"); setAmount(""); }}
                      className={`px-3 py-1 text-xs font-medium transition-colors ${
                        mode === "shares" ? (side === "buy" ? "bg-emerald-500 text-zinc-950" : "bg-rose-500 text-zinc-950") : "text-zinc-400 hover:bg-zinc-800"
                      }`}
                    >
                      Shares
                    </button>
                    <button
                      onClick={() => { setMode("dollars"); setAmount(""); }}
                      className={`px-3 py-1 text-xs font-medium transition-colors ${
                        mode === "dollars" ? (side === "buy" ? "bg-emerald-500 text-zinc-950" : "bg-rose-500 text-zinc-950") : "text-zinc-400 hover:bg-zinc-800"
                      }`}
                    >
                      Dollars
                    </button>
                  </div>
                </div>

                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 font-mono text-zinc-500">
                    {mode === "dollars" ? "$" : "#"}
                  </span>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="0"
                    min="0"
                    step={mode === "dollars" ? "0.01" : "1"}
                    className={`w-full rounded border border-zinc-800 bg-zinc-900 py-3 pl-8 pr-4 text-lg font-mono text-zinc-100 placeholder:text-zinc-700 focus:outline-none focus:ring-1 ${
                      side === "buy" ? "focus:border-emerald-500 focus:ring-emerald-500" : "focus:border-rose-500 focus:ring-rose-500"
                    }`}
                  />
                  {mode === "shares" && side === "sell" && position && (
                    <button
                      onClick={() => setAmount(position.quantity.toString())}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded bg-zinc-800 px-2 py-1 text-xs font-medium text-zinc-300 hover:bg-zinc-700 hover:text-white"
                    >
                      Max
                    </button>
                  )}
                </div>
              </div>

              {/* Estimate Display */}
              {amount && price && price > 0 ? (
                <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3 flex flex-col gap-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-zinc-400">Total {mode === "dollars" ? "Shares" : side === "buy" ? "Cost" : "Proceeds"}</span>
                    <span className="font-mono font-medium text-zinc-200">
                      {mode === "dollars" 
                        ? `${shares} shares @ ${formatPrice(price)}`
                        : formatPrice(costOrProceeds)}
                    </span>
                  </div>
                  {side === "sell" && position && (
                    <div className="flex justify-between text-sm border-t border-zinc-800/60 pt-2">
                      <span className="text-zinc-400">Estimated P&L</span>
                      <span className={`font-mono font-medium ${price >= position.avg_cost ? "text-emerald-400" : "text-rose-400"}`}>
                        {price >= position.avg_cost ? "+" : ""}{formatPrice((price - position.avg_cost) * shares)}
                      </span>
                    </div>
                  )}
                </div>
              ) : null}

              {error && <div className="text-sm text-rose-400">{error}</div>}

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setStep("select_side")}
                  className="flex-1 rounded border border-zinc-800 bg-zinc-900 py-2.5 font-medium text-zinc-300 hover:bg-zinc-800"
                >
                  Back
                </button>
                <button
                  onClick={handleConfirmReview}
                  disabled={!activeSymbol || !amount || !price || quoteQ.isLoading}
                  className={`flex-1 rounded py-2.5 font-semibold text-zinc-950 transition-colors disabled:opacity-50 ${
                    side === "buy" ? "bg-emerald-500 hover:bg-emerald-400" : "bg-rose-500 hover:bg-rose-400"
                  }`}
                >
                  Review Order
                </button>
              </div>
            </div>
          )}

          {step === "confirm" && (
            <div className="space-y-6 animate-fade-in">
              <div className="rounded-lg border border-zinc-800 text-sm">
                <div className="flex justify-between border-b border-zinc-800 p-3">
                  <span className="text-zinc-500">Action</span>
                  <span className={`font-semibold uppercase tracking-wide ${side === "buy" ? "text-emerald-400" : "text-rose-400"}`}>
                    {side}
                  </span>
                </div>
                <div className="flex justify-between border-b border-zinc-800 p-3">
                  <span className="text-zinc-500">Symbol</span>
                  <span className="font-mono font-medium text-zinc-200">{activeSymbol}</span>
                </div>
                <div className="flex justify-between border-b border-zinc-800 p-3">
                  <span className="text-zinc-500">Shares</span>
                  <span className="font-mono font-medium text-zinc-200">{shares} {shares === 1 ? 'share' : 'shares'}</span>
                </div>
                <div className="flex justify-between border-b border-zinc-800 p-3">
                  <span className="text-zinc-500">Execution Price</span>
                  <span className="font-mono font-medium text-zinc-200">{formatPrice(price!)}</span>
                </div>
                <div className="flex justify-between bg-zinc-900/50 p-3">
                  <span className="text-zinc-400">{side === "buy" ? "Total Cost" : "Estimated Proceeds"}</span>
                  <span className="font-mono font-semibold text-zinc-100">{formatPrice(costOrProceeds)}</span>
                </div>
              </div>

              {side === "buy" && portfolio && (
                <div className="text-center text-xs text-zinc-500">
                  Cash Required: <span className="font-mono">{formatPrice(costOrProceeds)}</span>
                  <br />
                  Cash Available: <span className="font-mono">{formatPrice(portfolio.cash)}</span>
                </div>
              )}

              {side === "sell" && position && price && (
                <div className="rounded-lg bg-zinc-900/50 p-3 text-center text-xs text-zinc-400">
                  Average Cost: <span className="font-mono">{formatPrice(position.avg_cost)}</span>
                  <br />
                  Estimated P&L on this trade:{" "}
                  <span className={`font-mono ${price >= position.avg_cost ? "text-emerald-400" : "text-rose-400"}`}>
                    {formatPrice((price - position.avg_cost) * shares)}
                  </span>
                </div>
              )}

              {error && <div className="text-center text-sm text-rose-400">{error}</div>}

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setStep("input")}
                  disabled={submitting}
                  className="flex-1 rounded border border-zinc-800 bg-zinc-900 py-2.5 font-medium text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
                >
                  Edit Order
                </button>
                <button
                  onClick={executeTrade}
                  disabled={submitting}
                  className={`flex-1 rounded py-2.5 font-semibold text-zinc-950 transition-colors disabled:opacity-50 ${
                    side === "buy" ? "bg-emerald-500 hover:bg-emerald-400" : "bg-rose-500 hover:bg-rose-400"
                  }`}
                >
                  {submitting ? "Executing..." : `Confirm ${side === "buy" ? "Buy" : "Sell"}`}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
