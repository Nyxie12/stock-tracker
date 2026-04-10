import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { heatmapApi } from "../api/heatmap";
import Heatmap from "../components/Heatmap";

type Universe = "sp500" | "watchlist";

export default function HeatmapPage() {
  const [universe, setUniverse] = useState<Universe>("sp500");
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const ro = new ResizeObserver(() => {
      setSize({ w: el.clientWidth, h: el.clientHeight });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const query = useQuery({
    queryKey: ["heatmap", universe],
    queryFn: () => heatmapApi.get(universe),
    refetchInterval: 60_000,
  });

  return (
    <div className="flex h-full flex-col space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Heatmap</h1>
        <div className="inline-flex overflow-hidden rounded border border-zinc-800 bg-zinc-900">
          {(["sp500", "watchlist"] as Universe[]).map((u) => (
            <button
              key={u}
              onClick={() => setUniverse(u)}
              className={`px-3 py-1 text-xs font-medium transition-colors ${
                universe === u ? "bg-emerald-500 text-zinc-950" : "text-zinc-400 hover:bg-zinc-800"
              }`}
            >
              {u === "sp500" ? "S&P top" : "Watchlist"}
            </button>
          ))}
        </div>
      </div>
      <div ref={containerRef} className="flex-1 rounded border border-zinc-800 bg-zinc-900/40 p-2">
        {query.isLoading && <div className="text-zinc-400">Loading heatmap…</div>}
        {query.isError && <div className="text-rose-400">Failed to load heatmap.</div>}
        {query.data && size.w > 0 && (
          <Heatmap rows={query.data.rows} width={size.w - 16} height={size.h - 16} />
        )}
        {query.data && query.data.rows.length === 0 && (
          <div className="text-zinc-400">No data (add Finnhub API key to populate).</div>
        )}
      </div>
    </div>
  );
}
