import { Link } from "react-router-dom";
import { Trash2 } from "lucide-react";
import { useTickerStore } from "../stores/tickerStore";
import { useTickerStream } from "../hooks/useTickerStream";
import type { WatchlistItem } from "../api/watchlist";
import { formatPct, formatPrice, pctClass } from "../lib/format";
import Sparkline from "./Sparkline";

type Props = {
  items: WatchlistItem[];
  onRemove: (symbol: string) => void;
};

export default function TickerTable({ items, onRemove }: Props) {
  const symbols = items.map((i) => i.symbol);
  useTickerStream(symbols);
  const ticks = useTickerStore((s) => s.ticks);

  if (items.length === 0) {
    return (
      <div className="rounded border border-zinc-800 bg-zinc-900/40 p-8 text-center text-zinc-400">
        No tickers yet. Add one above.
      </div>
    );
  }

  return (
    <table className="w-full border-collapse overflow-hidden rounded border border-zinc-800 text-sm">
      <thead className="bg-zinc-900/60 text-left text-xs uppercase tracking-wide text-zinc-400">
        <tr>
          <th className="px-4 py-2">Symbol</th>
          <th className="px-4 py-2">Name</th>
          <th className="px-4 py-2 text-right">Price</th>
          <th className="px-4 py-2 text-right">Change</th>
          <th className="px-4 py-2">Spark</th>
          <th className="px-4 py-2" />
        </tr>
      </thead>
      <tbody>
        {items.map((item) => {
          const tick = ticks[item.symbol];
          const live = tick?.price ?? item.last_price ?? null;
          let changePct = item.change_pct;
          if (live !== null && item.prev_close) {
            changePct = ((live - item.prev_close) / item.prev_close) * 100;
          }
          const flash =
            tick && tick.prevPrice !== null && tick.price !== tick.prevPrice
              ? tick.price > tick.prevPrice
                ? "bg-emerald-500/10"
                : "bg-rose-500/10"
              : "";
          return (
            <tr
              key={item.symbol}
              className={`border-t border-zinc-800 transition-colors ${flash}`}
            >
              <td className="px-4 py-2 font-mono font-semibold">
                <Link to={`/chart/${item.symbol}`} className="hover:text-emerald-400">
                  {item.symbol}
                </Link>
              </td>
              <td className="px-4 py-2 text-zinc-400">{item.name ?? "—"}</td>
              <td className="px-4 py-2 text-right font-mono">{formatPrice(live)}</td>
              <td className={`px-4 py-2 text-right font-mono ${pctClass(changePct)}`}>
                {formatPct(changePct)}
              </td>
              <td className="px-4 py-2">
                <Sparkline data={tick?.history ?? []} changePct={changePct} />
              </td>
              <td className="px-4 py-2 text-right">
                <button
                  onClick={() => onRemove(item.symbol)}
                  className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-rose-400"
                  aria-label={`Remove ${item.symbol}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
