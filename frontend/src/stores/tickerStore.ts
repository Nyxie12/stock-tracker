import { create } from "zustand";

export type TickState = {
  price: number;
  prevPrice: number | null;
  ts: number;
  // rolling window of recent prices for sparklines
  history: number[];
};

type TickerStore = {
  ticks: Record<string, TickState>;
  applyBatch: (ticks: { symbol: string; price: number; ts: number }[]) => void;
  clear: (symbol: string) => void;
};

const MAX_HISTORY = 120;

export const useTickerStore = create<TickerStore>((set) => ({
  ticks: {},
  applyBatch: (batch) =>
    set((state) => {
      if (batch.length === 0) return state;
      const next = { ...state.ticks };
      for (const { symbol, price, ts } of batch) {
        const prev = next[symbol];
        const history = prev ? [...prev.history, price] : [price];
        if (history.length > MAX_HISTORY) history.splice(0, history.length - MAX_HISTORY);
        next[symbol] = {
          price,
          prevPrice: prev ? prev.price : null,
          ts,
          history,
        };
      }
      return { ticks: next };
    }),
  clear: (symbol) =>
    set((state) => {
      if (!(symbol in state.ticks)) return state;
      const next = { ...state.ticks };
      delete next[symbol];
      return { ticks: next };
    }),
}));
