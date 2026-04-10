import { api } from "./client";

export type Position = {
  symbol: string;
  quantity: number;
  avg_cost: number;
  last_price: number | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
};

export type Portfolio = {
  cash: number;
  positions: Position[];
  market_value: number;
  total_value: number;
  initial_cash: number;
};

export type Trade = {
  id: number;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  executed_at: string;
};

export const paperApi = {
  portfolio: () => api.get<Portfolio>("/api/paper/portfolio"),
  trades: () => api.get<Trade[]>("/api/paper/trades"),
  buy: (symbol: string, quantity: number) =>
    api.post<Trade>("/api/paper/buy", { symbol, quantity }),
  sell: (symbol: string, quantity: number) =>
    api.post<Trade>("/api/paper/sell", { symbol, quantity }),
};
