import { api } from "./client";

export type Candle = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type Timeframe = "1D" | "1W" | "1M" | "1Y";

export type CandlesResponse = {
  symbol: string;
  timeframe: Timeframe;
  stale: boolean;
  candles: Candle[];
};

export const candlesApi = {
  get: (symbol: string, timeframe: Timeframe) =>
    api.get<CandlesResponse>(`/api/candles/${symbol}?timeframe=${timeframe}`),
};
