"""
TOOL: compare_companies

Per the spec: "Do not produce a simplistic winner. Present the underlying
data so the user can make their own assessment." This module therefore
returns structured, side-by-side data only — the LLM-written commentary
in the research agent is instructed the same way.
"""
from __future__ import annotations

from app.core.logging_config import get_logger
from app.models.schemas import ComparisonResult
from app.tools.fundamentals import get_company_fundamentals
from app.tools.news_sentiment import analyze_news_sentiment
from app.tools.technical_analysis import calculate_technical_indicators

log = get_logger("agents.compare")


def compare_companies(tickers: list[str]) -> ComparisonResult:
    log.info(f"[AGENT] compare_companies({tickers})")
    fundamentals, technicals, sentiment = {}, {}, {}

    for ticker in tickers:
        fundamentals[ticker] = get_company_fundamentals(ticker)
        technicals[ticker] = calculate_technical_indicators(ticker)
        sentiment[ticker] = analyze_news_sentiment(ticker)

    return ComparisonResult(
        tickers=[t.upper() for t in tickers],
        fundamentals=fundamentals,
        technicals=technicals,
        sentiment=sentiment,
        notes="Figures are as of the latest available data pull. This is informational, not investment advice.",
    )
