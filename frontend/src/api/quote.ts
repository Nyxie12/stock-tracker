import { api } from "./client";

export type Quote = {
  c: number; // current price
  d: number; // change
  dp: number; // percent change
  h: number; // high
  l: number; // low
  o: number; // open
  pc: number; // previous close
  t: number; // timestamp
};

export const quoteApi = {
  get: (symbol: string) => api.get<Quote>(`/api/quote/${symbol}`),
};
