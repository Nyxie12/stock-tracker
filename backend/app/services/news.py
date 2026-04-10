"""
News + sentiment service.

Fetches company news from Finnhub and scores each article's headline + summary
with VADER sentiment analysis. Returns articles annotated with a compound score
and a human-readable label (bullish / neutral / bearish).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

if TYPE_CHECKING:
    from .finnhub_client import FinnhubClient

log = logging.getLogger(__name__)

_analyzer = SentimentIntensityAnalyzer()

# Thresholds for labelling (VADER compound ranges from -1 to +1)
_BULLISH_THRESHOLD = 0.15
_BEARISH_THRESHOLD = -0.15


def _score_text(text: str) -> dict:
    """Return VADER scores dict with an added 'label' key."""
    scores = _analyzer.polarity_scores(text)
    compound = scores["compound"]
    if compound >= _BULLISH_THRESHOLD:
        label = "bullish"
    elif compound <= _BEARISH_THRESHOLD:
        label = "bearish"
    else:
        label = "neutral"
    return {"compound": round(compound, 4), "label": label}


async def fetch_news(
    finnhub: "FinnhubClient",
    symbol: str,
    days: int = 7,
) -> list[dict]:
    """Fetch company news and annotate with VADER sentiment."""
    to_date = date.today()
    from_date = to_date - timedelta(days=days)

    raw = await finnhub.company_news(
        symbol.upper(),
        from_date.isoformat(),
        to_date.isoformat(),
    )
    if not raw:
        return []

    articles: list[dict] = []
    for item in raw[:50]:  # cap at 50 articles to keep response light
        headline = item.get("headline", "")
        summary = item.get("summary", "")
        # Score on headline + summary combined for richer signal
        combined = f"{headline}. {summary}".strip()
        sentiment = _score_text(combined) if combined else _score_text("")

        articles.append(
            {
                "headline": headline,
                "summary": summary,
                "source": item.get("source", ""),
                "url": item.get("url", ""),
                "image": item.get("image", ""),
                "datetime": item.get("datetime", 0),
                "symbol": symbol.upper(),
                "sentiment": sentiment,
            }
        )

    # Sort newest first
    articles.sort(key=lambda a: a["datetime"], reverse=True)
    return articles
