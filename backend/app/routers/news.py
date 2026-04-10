from fastapi import APIRouter, Query, Request

from ..services.news import fetch_news

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("")
async def get_news(
    request: Request,
    symbol: str = Query("AAPL", min_length=1, max_length=16, description="Ticker symbol"),
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
) -> dict:
    """Fetch company news with VADER sentiment scores."""
    finnhub = request.app.state.finnhub
    articles = await fetch_news(finnhub, symbol, days)

    # Compute aggregate sentiment
    if articles:
        avg_compound = sum(a["sentiment"]["compound"] for a in articles) / len(articles)
        bullish = sum(1 for a in articles if a["sentiment"]["label"] == "bullish")
        bearish = sum(1 for a in articles if a["sentiment"]["label"] == "bearish")
        neutral = sum(1 for a in articles if a["sentiment"]["label"] == "neutral")
    else:
        avg_compound = 0.0
        bullish = bearish = neutral = 0

    return {
        "symbol": symbol.upper(),
        "article_count": len(articles),
        "aggregate": {
            "avg_compound": round(avg_compound, 4),
            "bullish": bullish,
            "neutral": neutral,
            "bearish": bearish,
        },
        "articles": articles,
    }
