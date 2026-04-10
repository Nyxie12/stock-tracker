import { create } from "zustand";

export type FiredAlert = {
  alertId: number;
  symbol: string;
  condition: string;
  threshold: number;
  price: number;
  firedAt: number;
};

type AlertStore = {
  recent: FiredAlert[];
  push: (alert: FiredAlert) => void;
};

const MAX = 50;

export const useAlertStore = create<AlertStore>((set) => ({
  recent: [],
  push: (alert) =>
    set((state) => {
      const next = [alert, ...state.recent];
      if (next.length > MAX) next.length = MAX;
      return { recent: next };
    }),
}));
