"""
TOOL: search_financial_news / analyze_news_sentiment

News source:
    Google News RSS — free and does not require an API key.

Sentiment:
    VADER — deterministic, lightweight and does not require an LLM.

Pipeline:

    Ticker
       ↓
    SEC/company name lookup
       ↓
    Google News RSS
       ↓
    NewsArticle
       ↓
    VADER sentiment
       ↓
    SentimentSummary

No paid API is required.
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from urllib.parse import quote

import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.core.cache import cache, cache_key
from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.models.schemas import (
    NewsArticle,
    Sentiment,
    SentimentSummary,
)

log = get_logger("tools.news_sentiment")

settings = get_settings()

_analyzer = SentimentIntensityAnalyzer()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_html(text: str | None) -> str | None:
    """Remove HTML from RSS summaries."""

    if not text:
        return None

    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _score_text(text: str) -> tuple[Sentiment, float]:
    """
    Returns:
        (sentiment label, compound score in [-1, 1])
    """

    compound = _analyzer.polarity_scores(text)["compound"]

    if compound >= 0.05:
        label = Sentiment.POSITIVE
    elif compound <= -0.05:
        label = Sentiment.NEGATIVE
    else:
        label = Sentiment.NEUTRAL

    return label, round(compound, 3)


# ---------------------------------------------------------------------------
# Google News RSS
# ---------------------------------------------------------------------------

def _fetch_news_rss(ticker: str) -> list[dict]:
    """
    Fetch recent financial news using Google News RSS.

    Example query:
        AAPL stock

    Google News returns RSS XML without requiring an API key.
    """

    ticker = ticker.upper().strip()

    query = quote(f"{ticker} stock")

    url = (
        "https://news.google.com/rss/search"
        f"?q={query}"
        "&hl=en-US"
        "&gl=US"
        "&ceid=US:en"
    )

    log.info(
        f"[NEWS] Fetching Google News RSS for {ticker}"
    )

    try:
        feed = feedparser.parse(url)

    except Exception as exc:
        log.warning(
            f"[NEWS] RSS request failed for {ticker}: {exc}"
        )
        return []

    if getattr(feed, "bozo", False):
        log.warning(
            f"[NEWS] Google News returned malformed RSS for {ticker}"
        )

    items = []

    for entry in feed.entries:
        items.append(
            {
                "title": entry.get("title"),
                "url": entry.get("link"),
                "summary": entry.get("summary"),
                "published": entry.get("published"),
                "source": (
                    entry.get("source", {}).get("title")
                    if isinstance(entry.get("source"), dict)
                    else None
                ),
            }
        )

    return items


# ---------------------------------------------------------------------------
# Public news function
# ---------------------------------------------------------------------------

def search_financial_news(
    ticker: str,
    limit: int | None = None,
) -> list[NewsArticle]:

    ticker = ticker.upper().strip()

    limit = limit or settings.max_news_articles

    key = cache_key(
        "news",
        ticker,
        str(limit),
    )

    if cached := cache.get(key):
        return cached

    log.info(
        f"[TOOL] search_financial_news({ticker})"
    )

    raw_items = _fetch_news_rss(ticker)

    if not raw_items:
        log.warning(
            f"[NEWS] No news found for {ticker}"
        )

        cache.set(
            key,
            [],
            ttl_seconds=600,
        )

        return []

    articles: list[NewsArticle] = []

    for item in raw_items[:limit]:

        title = item.get("title")

        if not title:
            continue

        url = item.get("url") or ""

        summary = _clean_html(
            item.get("summary")
        )

        source = item.get("source")

        published_at = item.get(
            "published"
        )

        # ---------------------------------------------------------------
        # Sentiment
        # ---------------------------------------------------------------

        sentiment_text = title

        if summary:
            sentiment_text += f". {summary}"

        label, score = _score_text(
            sentiment_text
        )

        article = NewsArticle(
            title=title,
            source=source,
            published_at=(
                str(published_at)
                if published_at
                else None
            ),
            url=url,
            summary=summary,
            sentiment=label,
            sentiment_score=score,
        )

        articles.append(article)

    cache.set(
        key,
        articles,
        ttl_seconds=600,
    )

    return articles


# ---------------------------------------------------------------------------
# Sentiment analysis
# ---------------------------------------------------------------------------

def analyze_news_sentiment(
    ticker: str,
) -> SentimentSummary:

    ticker = ticker.upper().strip()

    key = cache_key(
        "sentiment",
        ticker,
    )

    if cached := cache.get(key):
        return cached

    log.info(
        f"[TOOL] analyze_news_sentiment({ticker})"
    )

    articles = search_financial_news(
        ticker
    )

    if not articles:

        result = SentimentSummary(
            ticker=ticker,
            positive_pct=0,
            neutral_pct=0,
            negative_pct=0,
            article_count=0,
            articles=[],
        )

        cache.set(
            key,
            result,
            ttl_seconds=600,
        )

        return result

    counts = {
        Sentiment.POSITIVE: 0,
        Sentiment.NEUTRAL: 0,
        Sentiment.NEGATIVE: 0,
    }

    for article in articles:

        if article.sentiment:
            counts[article.sentiment] += 1

    total = len(articles)

    result = SentimentSummary(
        ticker=ticker,

        positive_pct=round(
            counts[Sentiment.POSITIVE]
            / total
            * 100,
            1,
        ),

        neutral_pct=round(
            counts[Sentiment.NEUTRAL]
            / total
            * 100,
            1,
        ),

        negative_pct=round(
            counts[Sentiment.NEGATIVE]
            / total
            * 100,
            1,
        ),

        article_count=total,

        articles=articles,
    )

    cache.set(
        key,
        result,
        ttl_seconds=600,
    )

    return result