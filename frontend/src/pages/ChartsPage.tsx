import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import PriceChart from "../components/PriceChart";
import TimeframeToggle from "../components/TimeframeToggle";
import { candlesApi, type Timeframe } from "../api/candles";
import { useTickerStream } from "../hooks/useTickerStream";
import { useTickerStore } from "../stores/tickerStore";
import { formatPrice } from "../lib/format";

export default function ChartsPage() {
  const { symbol = "AAPL" } = useParams();
  const sym = symbol.toUpperCase();
  const [tf, setTf] = useState<Timeframe>("1D");

  const symbols = useMemo(() => [sym], [sym]);
  useTickerStream(symbols);
  const livePrice = useTickerStore((s) => s.ticks[sym]?.price ?? null);

  const query = useQuery({
    queryKey: ["candles", sym, tf],
    queryFn: () => candlesApi.get(sym, tf),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <h1 className="text-2xl font-semibold font-mono">{sym}</h1>
          <span className="font-mono text-lg text-zinc-300">{formatPrice(livePrice)}</span>
          {query.data?.stale && (
            <span className="rounded bg-amber-500/20 px-2 py-0.5 text-xs text-amber-300">stale</span>
          )}
        </div>
        <TimeframeToggle value={tf} onChange={setTf} />
      </div>
      {query.isLoading && <div className="text-zinc-400">Loading candles…</div>}
      {query.isError && <div className="text-rose-400">Failed to load candles.</div>}
      {query.data && <PriceChart candles={query.data.candles} livePrice={livePrice} />}
    </div>
  );
}
