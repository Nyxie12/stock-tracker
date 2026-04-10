import { api } from "./client";

export type SentimentScore = {
  compound: number;
  label: "bullish" | "neutral" | "bearish";
};

export type NewsArticle = {
  headline: string;
  summary: string;
  source: string;
  url: string;
  image: string;
  datetime: number;
  symbol: string;
  sentiment: SentimentScore;
};

export type AggregateSentiment = {
  avg_compound: number;
  bullish: number;
  neutral: number;
  bearish: number;
};

export type NewsResponse = {
  symbol: string;
  article_count: number;
  aggregate: AggregateSentiment;
  articles: NewsArticle[];
};

export const newsApi = {
  get: (symbol: string, days: number = 7) =>
    api.get<NewsResponse>(`/api/news?symbol=${symbol}&days=${days}`),
};
