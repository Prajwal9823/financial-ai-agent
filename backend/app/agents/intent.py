"""
Intent detection.

The spec explicitly warns against an "uncontrolled autonomous agent" and
asks for a deterministic workflow where possible. Rather than asking the
LLM to freely decide which tools to call (which is slower, non-deterministic,
and harder to test), we classify the query into one of a fixed set of
intents with cheap keyword rules, and each intent maps to a *fixed* tool
plan in agent.py. The LLM's job is reasoning/synthesis over already-fetched
data, not deciding what data to fetch.

This is intentionally simple (no ML classifier) — it is easy to reason
about, easy to unit test, and transparent to the user via the tool trace
returned in the API response.
"""
from __future__ import annotations

import re
from enum import Enum


class Intent(str, Enum):
    STOCK_ANALYSIS = "STOCK_ANALYSIS"
    TECHNICAL_ANALYSIS = "TECHNICAL_ANALYSIS"
    FUNDAMENTAL_ANALYSIS = "FUNDAMENTAL_ANALYSIS"
    NEWS_ANALYSIS = "NEWS_ANALYSIS"
    SENTIMENT_ANALYSIS = "SENTIMENT_ANALYSIS"
    SEC_ANALYSIS = "SEC_ANALYSIS"
    COMPANY_COMPARISON = "COMPANY_COMPARISON"
    MARKET_OVERVIEW = "MARKET_OVERVIEW"
    GENERAL_FINANCIAL_QUESTION = "GENERAL_FINANCIAL_QUESTION"


# Common US tickers get matched directly; anything else falls back to
# scanning for 2-5 letter ALL-CAPS tokens, which is how most people type
# tickers ("Analyze NVDA", "compare AAPL and MSFT"). Minimum length 2
# (not 1) is deliberate: single letters are too noisy — abbreviations
# like "P/E" tokenize into stray "P" and "E" that would otherwise be
# misread as tickers. Trade-off: genuine single-letter tickers (F, T, X)
# won't be picked up by this simple heuristic; a production version would
# check candidates against a real ticker list instead.
_TICKER_PATTERN = re.compile(r"\b[A-Z]{2,5}\b")
_COMMON_WORDS_TO_IGNORE = {
    "I", "A", "THE", "OF", "TO", "IN", "ON", "IS", "IT", "VS", "AND", "OR",
    "WHY", "WHAT", "HOW", "FOR", "SEC", "CEO", "AI", "US", "USD", "EPS",
    "PE", "ROE", "RSI", "MACD",
}


def extract_tickers(query: str) -> list[str]:
    # Deliberately matched against the query AS TYPED, not query.upper().
    # Real tickers are conventionally already written in caps ("NVDA",
    # "AAPL"), while ordinary sentence words are lowercase or only
    # Title-cased (first letter only). Uppercasing the whole query first
    # (an earlier version of this function did) turns every short lowercase
    # word ("ratio", "give") into a false-positive ticker once forced to
    # caps — this way only tokens that were ALREADY all-caps count.
    candidates = _TICKER_PATTERN.findall(query)
    seen, tickers = set(), []
    for c in candidates:
        if c in _COMMON_WORDS_TO_IGNORE or c in seen:
            continue
        seen.add(c)
        tickers.append(c)
    return tickers


_INTENT_KEYWORDS: dict[Intent, list[str]] = {
    Intent.SEC_ANALYSIS: ["10-k", "10k", "10-q", "10q", "8-k", "8k", "sec filing", "annual report", "risk factors"],
    Intent.COMPANY_COMPARISON: ["compare", "vs", "versus", "against"],
    Intent.TECHNICAL_ANALYSIS: ["technical", "rsi", "macd", "moving average", "bollinger", "chart pattern", "sma", "ema"],
    Intent.FUNDAMENTAL_ANALYSIS: ["fundamental", "revenue", "earnings", "eps", "p/e", "pe ratio", "balance sheet", "profit margin"],
    Intent.NEWS_ANALYSIS: ["news", "headline", "recent development", "why did", "what happened"],
    Intent.SENTIMENT_ANALYSIS: ["sentiment", "how do investors feel", "bullish or bearish"],
    Intent.MARKET_OVERVIEW: ["market report", "market overview", "market insight"],
}


def detect_intent(query: str) -> Intent:
    q = query.lower()
    tickers = extract_tickers(query)

    # No ticker at all -> nothing for the analysis tools to run against,
    # regardless of keywords present (e.g. "What is a P/E ratio?" mentions
    # "P/E" but isn't asking about any specific company).
    if not tickers:
        return Intent.GENERAL_FINANCIAL_QUESTION

    if len(tickers) >= 2 and any(kw in q for kw in _INTENT_KEYWORDS[Intent.COMPANY_COMPARISON]):
        return Intent.COMPANY_COMPARISON

    for intent in (
        Intent.SEC_ANALYSIS,
        Intent.TECHNICAL_ANALYSIS,
        Intent.FUNDAMENTAL_ANALYSIS,
        Intent.SENTIMENT_ANALYSIS,
        Intent.NEWS_ANALYSIS,
        Intent.MARKET_OVERVIEW,
    ):
        if any(kw in q for kw in _INTENT_KEYWORDS[intent]):
            return intent

    # Ticker present but no specific-analysis keyword matched -> full
    # general-purpose stock analysis.
    return Intent.STOCK_ANALYSIS
