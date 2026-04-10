import { api } from "./client";

export type WatchlistItem = {
  symbol: string;
  added_at: string;
  name: string | null;
  last_price: number | null;
  prev_close: number | null;
  change_pct: number | null;
};

export const watchlistApi = {
  list: () => api.get<WatchlistItem[]>("/api/watchlist"),
  add: (symbol: string) => api.post<WatchlistItem>("/api/watchlist", { symbol }),
  remove: (symbol: string) => api.del<void>(`/api/watchlist/${symbol}`),
};
