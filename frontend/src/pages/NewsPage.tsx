import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ExternalLink,
  Newspaper,
  Search,
  TrendingDown,
  TrendingUp,
  Minus,
} from "lucide-react";
import { newsApi, type NewsResponse, type SentimentScore } from "../api/news";

/* ─── Helpers ───────────────────────────────────────────────────── */

function sentimentBadge(s: SentimentScore) {
  const config = {
    bullish: {
      bg: "bg-emerald-500/15",
      text: "text-emerald-400",
      Icon: TrendingUp,
    },
    neutral: {
      bg: "bg-amber-500/15",
      text: "text-amber-400",
      Icon: Minus,
    },
    bearish: {
      bg: "bg-rose-500/15",
      text: "text-rose-400",
      Icon: TrendingDown,
    },
  }[s.label];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${config.bg} ${config.text}`}
    >
      <config.Icon className="h-3 w-3" />
      {s.label}
      <span className="opacity-60">{s.compound.toFixed(2)}</span>
    </span>
  );
}

function timeAgo(unixSeconds: number): string {
  const diff = Math.floor(Date.now() / 1000 - unixSeconds);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/* ─── Sentiment Bar ─────────────────────────────────────────────── */

function SentimentBar({
  bullish,
  neutral,
  bearish,
  avgCompound,
}: {
  bullish: number;
  neutral: number;
  bearish: number;
  avgCompound: number;
}) {
  const total = bullish + neutral + bearish;
  if (total === 0) return null;
  const bPct = (bullish / total) * 100;
  const nPct = (neutral / total) * 100;
  const brPct = (bearish / total) * 100;

  const overallLabel =
    avgCompound >= 0.15 ? "Bullish" : avgCompound <= -0.15 ? "Bearish" : "Neutral";
  const overallColor =
    avgCompound >= 0.15
      ? "text-emerald-400"
      : avgCompound <= -0.15
        ? "text-rose-400"
        : "text-amber-400";

  return (
    <div className="card p-4 animate-fade-in">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
          Sentiment Overview
        </span>
        <span className={`text-sm font-semibold ${overallColor}`}>
          {overallLabel} ({avgCompound.toFixed(2)})
        </span>
      </div>
      <div className="flex h-2.5 overflow-hidden rounded-full">
        <div
          className="bg-emerald-500 transition-all"
          style={{ width: `${bPct}%` }}
          title={`Bullish: ${bullish}`}
        />
        <div
          className="bg-amber-400 transition-all"
          style={{ width: `${nPct}%` }}
          title={`Neutral: ${neutral}`}
        />
        <div
          className="bg-rose-500 transition-all"
          style={{ width: `${brPct}%` }}
          title={`Bearish: ${bearish}`}
        />
      </div>
      <div className="mt-2 flex gap-4 text-xs text-zinc-500">
        <span>
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-emerald-500" />
          Bullish {bullish}
        </span>
        <span>
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-amber-400" />
          Neutral {neutral}
        </span>
        <span>
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-rose-500" />
          Bearish {bearish}
        </span>
      </div>
    </div>
  );
}

/* ─── Main Page ─────────────────────────────────────────────────── */

export default function NewsPage() {
  const { symbol: routeSymbol } = useParams();
  const [input, setInput] = useState(routeSymbol?.toUpperCase() ?? "AAPL");
  const [activeSymbol, setActiveSymbol] = useState(input);
  const [days, setDays] = useState(7);

  const query = useQuery<NewsResponse>({
    queryKey: ["news", activeSymbol, days],
    queryFn: () => newsApi.get(activeSymbol, days),
    enabled: activeSymbol.length > 0,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim().toUpperCase();
    if (trimmed) setActiveSymbol(trimmed);
  };

  return (
    <div className="space-y-5 animate-fade-in">
      {/* ── Header + Search ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-zinc-100">News & Sentiment</h1>
        <div className="flex items-center gap-2">
          <form onSubmit={handleSearch} className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Symbol"
                className="w-32 rounded border border-zinc-800 bg-zinc-900 py-2 pl-8 pr-3 text-sm font-mono uppercase text-zinc-100 placeholder:text-zinc-600 focus:border-emerald-500 focus:outline-none"
              />
            </div>
            <button
              type="submit"
              className="rounded bg-emerald-500 px-3 py-2 text-sm font-semibold text-zinc-950 transition-colors hover:bg-emerald-400"
            >
              Search
            </button>
          </form>
          <div className="inline-flex overflow-hidden rounded border border-zinc-800 bg-zinc-900">
            {[3, 7, 14, 30].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-2.5 py-1 text-xs font-medium transition-colors ${
                  days === d
                    ? "bg-emerald-500 text-zinc-950"
                    : "text-zinc-400 hover:bg-zinc-800"
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Searching indicator ── */}
      {query.isLoading && (
        <div className="space-y-3">
          <div className="skeleton h-16 rounded-lg" />
          <div className="grid gap-3 md:grid-cols-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="skeleton h-40 rounded-lg" />
            ))}
          </div>
        </div>
      )}

      {query.isError && (
        <div className="card p-6 text-center text-rose-400">
          Failed to load news. Check your Finnhub API key.
        </div>
      )}

      {query.data && (
        <>
          {/* ── Sentiment Summary ── */}
          <SentimentBar
            bullish={query.data.aggregate.bullish}
            neutral={query.data.aggregate.neutral}
            bearish={query.data.aggregate.bearish}
            avgCompound={query.data.aggregate.avg_compound}
          />

          {/* ── Article Count ── */}
          <div className="text-xs text-zinc-500">
            {query.data.article_count} articles for{" "}
            <span className="font-mono font-semibold text-zinc-300">{query.data.symbol}</span>{" "}
            in the last {days} days
          </div>

          {/* ── No results ── */}
          {query.data.articles.length === 0 && (
            <div className="card flex flex-col items-center gap-2 p-10 text-zinc-500">
              <Newspaper className="h-10 w-10 opacity-30" />
              <span className="text-sm">No news found for {query.data.symbol}.</span>
            </div>
          )}

          {/* ── News Cards ── */}
          <div className="grid gap-3 md:grid-cols-2">
            {query.data.articles.map((article, idx) => (
              <a
                key={`${article.datetime}-${idx}`}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="card group flex gap-3 overflow-hidden p-0 transition-colors hover:border-zinc-600"
              >
                {/* Thumbnail */}
                {article.image && (
                  <div className="hidden w-32 shrink-0 sm:block">
                    <img
                      src={article.image}
                      alt=""
                      className="h-full w-full object-cover transition-transform group-hover:scale-105"
                      loading="lazy"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  </div>
                )}

                {/* Content */}
                <div className="flex flex-1 flex-col gap-1.5 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-sm font-semibold leading-snug text-zinc-200 group-hover:text-emerald-400 transition-colors line-clamp-2">
                      {article.headline}
                    </h3>
                    <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-600 group-hover:text-zinc-400" />
                  </div>

                  {article.summary && (
                    <p className="text-xs leading-relaxed text-zinc-500 line-clamp-2">
                      {article.summary}
                    </p>
                  )}

                  <div className="mt-auto flex items-center gap-2 pt-1">
                    {sentimentBadge(article.sentiment)}
                    <span className="text-xs text-zinc-600">
                      {article.source}
                    </span>
                    <span className="ml-auto text-xs text-zinc-600">
                      {timeAgo(article.datetime)}
                    </span>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
