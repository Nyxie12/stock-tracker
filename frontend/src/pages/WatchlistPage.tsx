import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import TickerTable from "../components/TickerTable";
import { watchlistApi, type WatchlistItem } from "../api/watchlist";

export default function WatchlistPage() {
  const qc = useQueryClient();
  const [symbol, setSymbol] = useState("");
  const [error, setError] = useState<string | null>(null);

  const query = useQuery<WatchlistItem[]>({
    queryKey: ["watchlist"],
    queryFn: watchlistApi.list,
  });

  const add = useMutation({
    mutationFn: (s: string) => watchlistApi.add(s),
    onSuccess: () => {
      setSymbol("");
      setError(null);
      qc.invalidateQueries({ queryKey: ["watchlist"] });
    },
    onError: (e: Error) => setError(e.message),
  });

  const remove = useMutation({
    mutationFn: (s: string) => watchlistApi.remove(s),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = symbol.trim().toUpperCase();
    if (!trimmed) return;
    add.mutate(trimmed);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Watchlist</h1>
      </div>
      <form onSubmit={onSubmit} className="flex items-center gap-2">
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Add symbol (e.g. AAPL)"
          className="w-64 rounded border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm font-mono uppercase focus:border-emerald-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={add.isPending}
          className="flex items-center gap-1 rounded bg-emerald-500 px-3 py-2 text-sm font-medium text-zinc-950 hover:bg-emerald-400 disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
          Add
        </button>
        {error && <span className="text-sm text-rose-400">{error}</span>}
      </form>
      {query.isLoading && <div className="text-zinc-400">Loading…</div>}
      {query.isError && <div className="text-rose-400">Failed to load watchlist.</div>}
      {query.data && <TickerTable items={query.data} onRemove={(s) => remove.mutate(s)} />}
    </div>
  );
}
