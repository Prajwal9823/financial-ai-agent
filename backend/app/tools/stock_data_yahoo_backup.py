"""
TOOL: get_stock_price / get_historical_prices / get_company_profile

Data source: yfinance (wraps Yahoo Finance's public endpoints).
Chosen over Alpha Vantage as the default because it needs no API key and
has no hard daily request cap, which matters a lot for a demo/portfolio
project. Alpha Vantage remains supported (see fundamentals.py) as a
secondary source and can be swapped in here the same way if preferred.

Every function raises `TickerNotFoundError` on bad input instead of
returning fabricated numbers — see rule #3/#6 in the project's dev rules.
"""
from __future__ import annotations

from datetime import datetime, timezone

import yfinance as yf

from app.core.cache import cache, cache_key
from app.core.logging_config import get_logger
from app.core.rate_limiter import with_retry
from app.models.schemas import (
    CompanyProfile,
    HistoricalPrices,
    HistoricalPricePoint,
    StockPrice,
)

log = get_logger("tools.stock_data")

_COMMON_NAME_TO_TICKER = {
    "APPLE": "AAPL", "MICROSOFT": "MSFT", "GOOGLE": "GOOGL", "ALPHABET": "GOOGL",
    "AMAZON": "AMZN", "META": "META", "FACEBOOK": "META", "TESLA": "TSLA",
    "NVIDIA": "NVDA", "NETFLIX": "NFLX",
}


class TickerNotFoundError(Exception):
    """Raised when the upstream data source has no data for a ticker."""


def get_ticker_handle(symbol: str) -> yf.Ticker:
    """Shared yfinance Ticker factory — reused by other tool modules
    (technical_analysis, news_sentiment) so there's a single place that
    knows how to normalize a ticker symbol."""
    return yf.Ticker(symbol.upper().strip())


def _friendly_not_found(ticker: str, cause: Exception) -> TickerNotFoundError:
    """yfinance raises raw, low-level errors (KeyError, JSONDecodeError)
    for BOTH 'this ticker doesn't exist' and 'Yahoo is rate-limiting us'
    — it doesn't distinguish them, so neither can we with certainty. This
    turns either case into one clean, actionable message instead of a
    500 stack trace, with a nudge toward the single most common cause:
    someone searched a company NAME ("APPLE") instead of its ticker
    SYMBOL ("AAPL")."""
    upper = ticker.upper().strip()
    suggestion = _COMMON_NAME_TO_TICKER.get(upper)
    if suggestion:
        msg = f"'{ticker}' isn't a stock ticker — did you mean '{suggestion}'? Search by ticker symbol, not company name."
    else:
        msg = (
            f"Couldn't retrieve data for '{ticker}'. Either it isn't a valid ticker symbol, "
            f"or Yahoo Finance is temporarily rate-limiting requests — try again in a minute."
        )
    log.warning(f"[TOOL] {ticker}: {msg} (root cause: {cause})")
    # Short negative cache: a bad/blocked ticker shouldn't re-hit Yahoo on
    # every repeated click within the next couple minutes — that's exactly
    # the kind of burst that gets an IP rate-limited in the first place.
    cache.set(cache_key("bad_ticker", ticker), msg, ttl_seconds=120)
    return TickerNotFoundError(msg)


def _raise_if_recently_failed(ticker: str) -> None:
    if cached_msg := cache.get(cache_key("bad_ticker", ticker)):
        raise TickerNotFoundError(cached_msg)


@with_retry()
def _fetch_fast_info(ticker: str) -> dict:
    return dict(get_ticker_handle(ticker).fast_info)


@with_retry()
def _fetch_history(ticker: str, period: str, interval: str):
    return get_ticker_handle(ticker).history(period=period, interval=interval)


@with_retry()
def get_cached_info(ticker: str) -> dict:
    """The heavy `.info` scrape (quoteSummary — several modules in one
    call) is what Yahoo rate-limits hardest. Both get_company_profile()
    and fundamentals.py's get_company_fundamentals() used to each fetch it
    separately; this shared, longer-TTL cache means a single search now
    hits that endpoint at most once instead of twice. Callers are
    responsible for checking `_raise_if_recently_failed()` first — doing
    it here too would mean even a cache-hit short-circuit pays the
    lock/throttle cost this decorator adds."""
    key = cache_key("raw_info", ticker)
    if cached := cache.get(key):
        return cached
    info = get_ticker_handle(ticker).info
    cache.set(key, info, ttl_seconds=6 * 3600)
    return info


def get_stock_price(ticker: str) -> StockPrice:
    """Current/most-recent price snapshot for a single ticker."""
    key = cache_key("price", ticker)
    if cached := cache.get(key):
        return cached
    _raise_if_recently_failed(ticker)

    log.info(f"[TOOL] get_stock_price({ticker})")
    try:
        info = _fetch_fast_info(ticker)  # lightweight, avoids the heavy .info scrape
    except Exception as exc:  # noqa: BLE001 - yfinance raises raw KeyError/JSONDecodeError for both bad tickers and rate limits
        raise _friendly_not_found(ticker, exc) from exc

    if not info or info.get("lastPrice") is None:
        raise TickerNotFoundError(f"No price data found for ticker '{ticker}'.")

    last_price = float(info["lastPrice"])
    prev_close = float(info.get("previousClose") or last_price)
    change = last_price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0.0

    result = StockPrice(
        ticker=ticker.upper(),
        price=round(last_price, 2),
        change=round(change, 2),
        change_percent=round(change_pct, 2),
        market_cap=info.get("marketCap"),
        as_of=datetime.now(timezone.utc).isoformat(),
    )
    cache.set(key, result, ttl_seconds=60)  # prices go stale fast
    return result


def get_historical_prices(ticker: str, period: str = "1y", interval: str = "1d") -> HistoricalPrices:
    """
    period: e.g. '1mo', '3mo', '6mo', '1y', '5y'
    interval: e.g. '1d', '1wk', '1mo'
    """
    key = cache_key("history", ticker, period, interval)
    if cached := cache.get(key):
        return cached
    _raise_if_recently_failed(ticker)

    log.info(f"[TOOL] get_historical_prices({ticker}, {period}, {interval})")
    try:
        df = _fetch_history(ticker, period, interval)
    except Exception as exc:  # noqa: BLE001
        raise _friendly_not_found(ticker, exc) from exc

    if df.empty:
        raise TickerNotFoundError(f"No historical data found for ticker '{ticker}'.")

    points = [
        HistoricalPricePoint(
            date=idx.strftime("%Y-%m-%d"),
            open=round(float(row["Open"]), 2),
            high=round(float(row["High"]), 2),
            low=round(float(row["Low"]), 2),
            close=round(float(row["Close"]), 2),
            volume=int(row["Volume"]),
        )
        for idx, row in df.iterrows()
    ]

    result = HistoricalPrices(ticker=ticker.upper(), period=period, interval=interval, points=points)
    cache.set(key, result)
    return result


def get_company_profile(ticker: str) -> CompanyProfile:
    key = cache_key("profile", ticker)
    if cached := cache.get(key):
        return cached
    _raise_if_recently_failed(ticker)

    log.info(f"[TOOL] get_company_profile({ticker})")
    try:
        info = get_cached_info(ticker)
    except Exception as exc:  # noqa: BLE001
        raise _friendly_not_found(ticker, exc) from exc

    if not info or info.get("shortName") is None:
        raise TickerNotFoundError(f"No company profile found for ticker '{ticker}'.")

    result = CompanyProfile(
        ticker=ticker.upper(),
        name=info.get("shortName") or info.get("longName") or ticker.upper(),
        sector=info.get("sector"),
        industry=info.get("industry"),
        description=info.get("longBusinessSummary"),
        website=info.get("website"),
        employees=info.get("fullTimeEmployees"),
    )
    cache.set(key, result, ttl_seconds=6 * 3600)  # profile rarely changes
    return result
