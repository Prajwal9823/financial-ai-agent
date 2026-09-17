"""
API routes.

Each single-purpose endpoint (GET /api/stock/{ticker}/...) lets the
frontend fetch one piece of data directly without going through the LLM —
useful for charts/tables that don't need narrative text. The two POST
endpoints (/api/research, /api/compare) are where the actual agent runs.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents.agent import run_research_agent
from app.agents.compare import compare_companies
from app.models.schemas import (
    CompanyProfile,
    CompareRequest,
    ComparisonResult,
    Fundamentals,
    HistoricalPrices,
    ResearchRequest,
    ResearchResponse,
    SecFilingAnswer,
    SentimentSummary,
    StockPrice,
    TechnicalIndicators,
)
from app.tools.fundamentals import get_company_fundamentals
from app.tools.news_sentiment import analyze_news_sentiment
from app.tools.sec_filings import FilingNotFoundError, search_sec_filings
from app.tools.stock_data import (
    TickerNotFoundError,
    get_company_profile,
    get_historical_prices,
    get_stock_price,
)
from app.tools.technical_analysis import calculate_technical_indicators

router = APIRouter(prefix="/api")


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.get("/stock/{ticker}", response_model=StockPrice)
def stock_price(ticker: str) -> StockPrice:
    try:
        return get_stock_price(ticker)
    except TickerNotFoundError as exc:
        raise _not_found(exc)


@router.get("/stock/{ticker}/profile", response_model=CompanyProfile)
def stock_profile(ticker: str) -> CompanyProfile:
    try:
        return get_company_profile(ticker)
    except TickerNotFoundError as exc:
        raise _not_found(exc)


@router.get("/stock/{ticker}/history", response_model=HistoricalPrices)
def stock_history(ticker: str, period: str = "1y", interval: str = "1d") -> HistoricalPrices:
    try:
        return get_historical_prices(ticker, period=period, interval=interval)
    except TickerNotFoundError as exc:
        raise _not_found(exc)


@router.get("/stock/{ticker}/fundamentals", response_model=Fundamentals)
def stock_fundamentals(ticker: str) -> Fundamentals:
    try:
        return get_company_fundamentals(ticker)
    except TickerNotFoundError as exc:
        raise _not_found(exc)


@router.get("/stock/{ticker}/technicals", response_model=TechnicalIndicators)
def stock_technicals(ticker: str) -> TechnicalIndicators:
    try:
        return calculate_technical_indicators(ticker)
    except TickerNotFoundError as exc:
        raise _not_found(exc)


@router.get("/stock/{ticker}/news", response_model=SentimentSummary)
def stock_news(ticker: str) -> SentimentSummary:
    try:
        return analyze_news_sentiment(ticker)
    except TickerNotFoundError as exc:
        raise _not_found(exc)


@router.get("/stock/{ticker}/sentiment", response_model=SentimentSummary)
def stock_sentiment(ticker: str) -> SentimentSummary:
    # Same underlying data as /news — kept as a separate route because the
    # spec lists them as distinct concerns on the frontend (a sentiment
    # donut chart vs a news-card list).
    try:
        return analyze_news_sentiment(ticker)
    except TickerNotFoundError as exc:
        raise _not_found(exc)


@router.get("/stock/{ticker}/filings", response_model=SecFilingAnswer)
def stock_filings(ticker: str, question: str = "key risks and financial highlights", form_type: str = "10-K") -> SecFilingAnswer:
    try:
        chunks = search_sec_filings(ticker, question=question, form_type=form_type)
    except FilingNotFoundError as exc:
        raise _not_found(exc)

    if not chunks:
        answer = "No relevant sections were found in the latest filing for this question."
    else:
        answer = "Relevant excerpts retrieved — see chunks_used for the grounding text and source filing."

    return SecFilingAnswer(ticker=ticker.upper(), question=question, answer=answer, chunks_used=chunks)


@router.post("/research", response_model=ResearchResponse)
async def research(payload: ResearchRequest) -> ResearchResponse:
    return await run_research_agent(payload.query)


@router.post("/compare", response_model=ComparisonResult)
def compare(payload: CompareRequest) -> ComparisonResult:
    try:
        return compare_companies(payload.tickers)
    except TickerNotFoundError as exc:
        raise _not_found(exc)
