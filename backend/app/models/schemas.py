"""
Pydantic schemas — the single source of truth for API request/response
shapes. Keeping these separate from business logic makes it trivial to
generate an accurate OpenAPI/Swagger doc (FastAPI does this automatically
from these classes at /docs).
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class DataAvailability(BaseModel):
    """Marks whether a numeric field was actually retrieved, so the
    frontend/LLM never mistakes a placeholder for a real number."""
    value: Optional[float] = None
    available: bool = True
    note: Optional[str] = None  # e.g. "Not available from the current data source."


# ---------------------------------------------------------------------------
# Stock price / history
# ---------------------------------------------------------------------------

class StockPrice(BaseModel):
    ticker: str
    price: float
    currency: str = "USD"
    change: float
    change_percent: float
    market_cap: Optional[float] = None
    as_of: str


class HistoricalPricePoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoricalPrices(BaseModel):
    ticker: str
    period: str
    interval: str
    points: list[HistoricalPricePoint]


# ---------------------------------------------------------------------------
# Fundamentals
# ---------------------------------------------------------------------------

class CompanyProfile(BaseModel):
    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    employees: Optional[int] = None


class Fundamentals(BaseModel):
    ticker: str
    revenue_ttm: Optional[float] = None
    revenue_growth: Optional[float] = None
    net_income_ttm: Optional[float] = None
    eps_ttm: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    free_cash_flow: Optional[float] = None
    earnings_growth: Optional[float] = None
    unavailable_fields: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Technical analysis
# ---------------------------------------------------------------------------

class TechnicalIndicators(BaseModel):
    ticker: str
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_20: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_trend: Optional[str] = None  # Bullish / Bearish / Neutral
    rsi_14: Optional[float] = None
    stochastic_k: Optional[float] = None
    stochastic_d: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    historical_volatility: Optional[float] = None
    max_drawdown: Optional[float] = None
    return_1d: Optional[float] = None
    return_1w: Optional[float] = None
    return_1m: Optional[float] = None
    return_3m: Optional[float] = None
    return_1y: Optional[float] = None


# ---------------------------------------------------------------------------
# News + sentiment
# ---------------------------------------------------------------------------

class NewsArticle(BaseModel):
    title: str
    source: Optional[str] = None
    published_at: Optional[str] = None
    url: str
    summary: Optional[str] = None
    sentiment: Optional[Sentiment] = None
    sentiment_score: Optional[float] = None


class SentimentSummary(BaseModel):
    ticker: str
    positive_pct: float
    neutral_pct: float
    negative_pct: float
    article_count: int
    articles: list[NewsArticle]


# ---------------------------------------------------------------------------
# SEC filings / RAG
# ---------------------------------------------------------------------------

class FilingReference(BaseModel):
    ticker: str
    form_type: str
    filing_date: str
    accession_number: str
    url: str


class RetrievedChunk(BaseModel):
    text: str
    source: FilingReference
    section: Optional[str] = None
    relevance_score: float


class SecFilingAnswer(BaseModel):
    ticker: str
    question: str
    answer: str
    chunks_used: list[RetrievedChunk]


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

class ComparisonResult(BaseModel):
    tickers: list[str]
    fundamentals: dict[str, Fundamentals]
    technicals: dict[str, TechnicalIndicators]
    sentiment: dict[str, SentimentSummary]
    notes: str


# ---------------------------------------------------------------------------
# Research agent (chat) endpoint
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural-language question, e.g. 'Analyze NVDA'")


class ToolTrace(BaseModel):
    tool: str
    status: str  # "success" | "error" | "skipped"


class ResearchResponse(BaseModel):
    query: str
    intent: str
    tools_used: list[ToolTrace]
    answer: str
    sources: list[str]
    raw_data: dict[str, Any] = Field(default_factory=dict)


class CompareRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=2, max_length=4)
