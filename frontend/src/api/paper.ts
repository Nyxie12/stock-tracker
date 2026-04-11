import { api } from "./client";

export type Position = {
  symbol: string;
  quantity: number;
  avg_cost: number;
  last_price: number | null;
  prev_close: number | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  day_change: number | null;
  day_change_pct: number | null;
};

export type PendingSettlement = {
  amount: number;
  settles_at: string;
};

export type MarketStatus = {
  open: boolean;
  session: "pre" | "regular" | "post" | "closed";
  next_open_iso: string;
  now_iso: string;
};

export type Portfolio = {
  cash: number;
  buying_power: number;
  pending_settlement: number;
  reserved_for_orders: number;
  pending_settlements: PendingSettlement[];
  positions: Position[];
  market_value: number;
  total_value: number;
  initial_cash: number;
  realized_pnl: number;
  market_status: MarketStatus;
};

export type Trade = {
  id: number;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  realized_pnl: number | null;
  executed_at: string;
};

export type LimitOrder = {
  id: number;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  limit_price: number;
  status: string;
  created_at: string;
  filled_at: string | null;
};

export const paperApi = {
  portfolio: () => api.get<Portfolio>("/api/paper/portfolio"),
  trades: () => api.get<Trade[]>("/api/paper/trades"),
  buy: (symbol: string, quantity: number) =>
    api.post<Trade>("/api/paper/buy", { symbol, quantity }),
  sell: (symbol: string, quantity: number) =>
    api.post<Trade>("/api/paper/sell", { symbol, quantity }),
  reset: () => api.post<Portfolio>("/api/paper/reset", {}),
  marketStatus: () => api.get<MarketStatus>("/api/paper/market-status"),
  listOrders: () => api.get<LimitOrder[]>("/api/paper/orders"),
  placeOrder: (params: {
    symbol: string;
    side: "buy" | "sell";
    quantity: number;
    limit_price: number;
  }) => api.post<LimitOrder>("/api/paper/orders", params),
  cancelOrder: (id: number) => api.del<LimitOrder>(`/api/paper/orders/${id}`),
};
