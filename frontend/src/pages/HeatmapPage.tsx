import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { heatmapApi, type HeatmapUniverse } from "../api/heatmap";
import Heatmap from "../components/Heatmap";

const UNIVERSE_LABELS: Record<HeatmapUniverse, string> = {
  sp500: "S&P top",
  nasdaq: "Nasdaq 100",
  watchlist: "Watchlist",
};

// Poll intervals per universe (ms). Fixed universes match the backend
// refresh cadence; watchlist is a bit tighter since it's user-driven.
const REFETCH_INTERVAL: Record<HeatmapUniverse, number> = {
  sp500: 300_000,
  nasdaq: 600_000,
  watchlist: 120_000,
};

function formatRelative(updatedAt: number | null): string {
  if (!updatedAt) return "never";
  const diffS = Math.max(0, Date.now() / 1000 - updatedAt);
  if (diffS < 60) return `${Math.floor(diffS)}s ago`;
  if (diffS < 3600) return `${Math.floor(diffS / 60)}m ago`;
  if (diffS < 86400) return `${Math.floor(diffS / 3600)}h ago`;
  return `${Math.floor(diffS / 86400)}d ago`;
}

export default function HeatmapPage() {
  const [universe, setUniverse] = useState<HeatmapUniverse>("sp500");
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  // Tick every 15s so the "last updated" label stays roughly accurate without
  // re-fetching data.
  const [, setNowTick] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => setNowTick((n) => n + 1), 15_000);
    return () => window.clearInterval(id);
  }, []);

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
    refetchInterval: (q) => {
      // While the backend is still warming up, poll faster so the first
      // paint after a cold start lands quickly.
      if (q.state.data?.building) return 5_000;
      return REFETCH_INTERVAL[universe];
    },
  });

  const lastUpdatedLabel = useMemo(
    () => formatRelative(query.data?.last_updated ?? null),
    // Re-compute on data change and on the 15s tick.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [query.data?.last_updated, query.dataUpdatedAt],
  );

  return (
    <div className="flex h-full flex-col space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Heatmap</h1>
        <div className="flex items-center gap-3">
          {query.data && (
            <div className="flex items-center gap-2 text-xs text-zinc-400">
              {query.data.stale && (
                <span
                  className="h-1.5 w-1.5 rounded-full bg-amber-400"
                  title="Refreshing in the background"
                />
              )}
              <span>Updated {lastUpdatedLabel}</span>
            </div>
          )}
          <div className="inline-flex overflow-hidden rounded border border-zinc-800 bg-zinc-900">
            {(Object.keys(UNIVERSE_LABELS) as HeatmapUniverse[]).map((u) => (
              <button
                key={u}
                onClick={() => setUniverse(u)}
                className={`px-3 py-1 text-xs font-medium transition-colors ${
                  universe === u
                    ? "bg-emerald-500 text-zinc-950"
                    : "text-zinc-400 hover:bg-zinc-800"
                }`}
              >
                {UNIVERSE_LABELS[u]}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div
        ref={containerRef}
        className="flex-1 rounded border border-zinc-800 bg-zinc-900/40 p-2"
      >
        {query.isLoading && (
          <div className="text-zinc-400">Loading heatmap…</div>
        )}
        {query.isError && (
          <div className="text-rose-400">Failed to load heatmap.</div>
        )}
        {query.data?.building && query.data.rows.length === 0 && (
          <div className="text-zinc-400">
            Warming up heatmap… first refresh takes a moment after a cold start.
          </div>
        )}
        {query.data && query.data.rows.length > 0 && size.w > 0 && (
          <Heatmap
            rows={query.data.rows}
            width={size.w - 16}
            height={size.h - 16}
          />
        )}
        {query.data &&
          !query.data.building &&
          query.data.rows.length === 0 && (
            <div className="text-zinc-400">
              No data (add Finnhub API key to populate).
            </div>
          )}
      </div>
    </div>
  );
}
