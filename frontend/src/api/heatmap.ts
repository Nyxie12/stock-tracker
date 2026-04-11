import { api } from "./client";

export type HeatmapUniverse = "sp500" | "nasdaq" | "watchlist";

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
  universe: HeatmapUniverse;
  rows: HeatmapRow[];
  last_updated: number | null;
  stale: boolean;
  building: boolean;
};

export const heatmapApi = {
  get: (universe: HeatmapUniverse) =>
    api.get<HeatmapResponse>(`/api/heatmap?universe=${universe}`),
};
