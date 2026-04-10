import { api } from "./client";

export type HeatmapRow = {
  symbol: string;
  name: string;
  sector: string;
  marketCap: number;
  price: number;
  prevClose: number;
  changePct: number;
};

export type HeatmapResponse = {
  universe: "sp500" | "watchlist";
  rows: HeatmapRow[];
};

export const heatmapApi = {
  get: (universe: "sp500" | "watchlist") =>
    api.get<HeatmapResponse>(`/api/heatmap?universe=${universe}`),
};
