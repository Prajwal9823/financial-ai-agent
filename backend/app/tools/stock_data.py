from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO

import pandas as pd
import requests
import time
from datetime import datetime, timedelta, timezone

from app.core.cache import cache, cache_key
from app.core.logging_config import get_logger
from app.models.schemas import (
    CompanyProfile,
    HistoricalPrices,
    HistoricalPricePoint,
    StockPrice,
)

log = get_logger("tools.stock_data")
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SEC_HEADERS = {
    "User-Agent": "FinancialAIAgent research-project contact@example.com"
}

STOOQ_URL = "https://stooq.com/q/d/l/"


_COMMON_NAME_TO_TICKER = {
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "GOOGLE": "GOOGL",
    "ALPHABET": "GOOGL",
    "AMAZON": "AMZN",
    "META": "META",
    "FACEBOOK": "META",
    "TESLA": "TSLA",
    "NVIDIA": "NVDA",
    "NETFLIX": "NFLX",
}


class TickerNotFoundError(Exception):
    """Raised when a free upstream data source has no data for a ticker."""


# ---------------------------------------------------------------------------
# SEC ticker / CIK mapping
# ---------------------------------------------------------------------------

_sec_ticker_map: dict[str, dict] | None = None


def _load_sec_ticker_map() -> dict[str, dict]:
    global _sec_ticker_map

    if _sec_ticker_map is not None:
        return _sec_ticker_map

    log.info("[SEC] Loading ticker -> CIK map")

    response = requests.get(
        "https://www.sec.gov/files/company_tickers.json",
        headers=SEC_HEADERS,
        timeout=20,
    )
    response.raise_for_status()

    raw = response.json()

    result: dict[str, dict] = {}

    for item in raw.values():
        ticker = str(item.get("ticker", "")).upper().strip()

        if ticker:
            result[ticker] = {
                "cik": str(item["cik_str"]).zfill(10),
                "name": item.get("title"),
            }

    _sec_ticker_map = result
    return result


def _get_sec_company(ticker: str) -> dict:
    ticker = ticker.upper().strip()

    mapping = _load_sec_ticker_map()

    if ticker not in mapping:
        raise TickerNotFoundError(
            f"Ticker '{ticker}' was not found in the SEC company database."
        )

    return mapping[ticker]


# ---------------------------------------------------------------------------
# Stooq market data
# ---------------------------------------------------------------------------

def _stooq_symbol(ticker: str) -> str:
    return f"{ticker.lower().strip()}.us"


def _fetch_yahoo_chart(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:

    ticker = ticker.upper().strip()

    url = f"{YAHOO_CHART_URL}/{ticker}"

    params = {
        "range": period,
        "interval": interval,
        "events": "div,splits",
        "includePrePost": "false",
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=20,
    )

    log.info(
        f"[YAHOO-CHART] {ticker}: HTTP {response.status_code}"
    )

    if response.status_code == 429:
        raise TickerNotFoundError(
            "Yahoo Chart endpoint is currently rate-limiting requests. "
            "Please wait a minute and try again."
        )

    response.raise_for_status()

    data = response.json()

    chart = data.get("chart", {})

    if chart.get("error"):
        error = chart["error"]

        raise TickerNotFoundError(
            error.get(
                "description",
                f"Yahoo returned an error for {ticker}",
            )
        )

    results = chart.get("result")

    if not results:
        raise TickerNotFoundError(
            f"No Yahoo chart data found for '{ticker}'."
        )

    result = results[0]

    timestamps = result.get("timestamp")

    indicators = result.get(
        "indicators",
        {},
    )

    quotes = indicators.get(
        "quote",
        [],
    )

    if not timestamps or not quotes:
        raise TickerNotFoundError(
            f"Yahoo returned no OHLCV data for '{ticker}'."
        )

    quote = quotes[0]

    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                timestamps,
                unit="s",
                utc=True,
            ).tz_convert(None),
            "Open": quote.get("open"),
            "High": quote.get("high"),
            "Low": quote.get("low"),
            "Close": quote.get("close"),
            "Volume": quote.get("volume"),
        }
    )

    # Remove rows where price data is unavailable.
    df = df.dropna(
        subset=[
            "Open",
            "High",
            "Low",
            "Close",
        ]
    )

    if df.empty:
        raise TickerNotFoundError(
            f"No valid price data returned for '{ticker}'."
        )

    for column in [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df["Volume"] = df["Volume"].fillna(0)

    df = (
        df.sort_values("Date")
        .drop_duplicates("Date")
        .reset_index(drop=True)
    )

    return df


# ---------------------------------------------------------------------------
# Compatibility helper
# ---------------------------------------------------------------------------

def get_ticker_handle(symbol: str):
    """
    Compatibility function for older modules.

    New code should use the explicit free-data functions instead.
    """
    return symbol.upper().strip()


# ---------------------------------------------------------------------------
# Friendly errors
# ---------------------------------------------------------------------------

def _friendly_not_found(
    ticker: str,
    cause: Exception,
) -> TickerNotFoundError:

    upper = ticker.upper().strip()

    suggestion = _COMMON_NAME_TO_TICKER.get(upper)

    if suggestion:
        msg = (
            f"'{ticker}' isn't a stock ticker — "
            f"did you mean '{suggestion}'? "
            f"Search by ticker symbol, not company name."
        )
    else:
        msg = (
            f"Couldn't retrieve free market data for '{ticker}'. "
            f"Check the ticker symbol and try again."
        )

    log.warning(
        f"[TOOL] {ticker}: {msg} "
        f"(root cause: {cause})"
    )

    return TickerNotFoundError(msg)


# ---------------------------------------------------------------------------
# Current price
# ---------------------------------------------------------------------------

def get_stock_price(ticker: str) -> StockPrice:

    ticker = ticker.upper().strip()

    key = cache_key("price", ticker)

    if cached := cache.get(key):
        return cached

    log.info(f"[TOOL] get_stock_price({ticker})")

    try:
        df = _fetch_yahoo_chart(
            ticker,
            period="5d",
            interval="1d",
        )

    except Exception as exc:
        raise _friendly_not_found(ticker, exc) from exc

    if df.empty:
        raise TickerNotFoundError(
            f"No price data found for '{ticker}'."
        )

    last = df.iloc[-1]

    last_price = float(last["Close"])

    previous_close = (
        float(df.iloc[-2]["Close"])
        if len(df) >= 2
        else last_price
    )

    change = last_price - previous_close

    change_pct = (
        (change / previous_close) * 100
        if previous_close
        else 0.0
    )

    result = StockPrice(
        ticker=ticker,
        price=round(last_price, 2),
        change=round(change, 2),
        change_percent=round(change_pct, 2),
        market_cap=None,
        as_of=str(last["Date"]),
    )

    cache.set(
        key,
        result,
        ttl_seconds=300,
    )

    return result


# ---------------------------------------------------------------------------
# Historical prices
# ---------------------------------------------------------------------------

def get_historical_prices(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> HistoricalPrices:

    ticker = ticker.upper().strip()

    key = cache_key(
        "history",
        ticker,
        period,
        interval,
    )

    if cached := cache.get(key):
        return cached

    log.info(
        f"[TOOL] get_historical_prices("
        f"{ticker}, {period}, {interval})"
    )

    # Approximate calendar lookback.
    days = {
        "1mo": 40,
        "3mo": 120,
        "6mo": 220,
        "1y": 400,
        "2y": 800,
        "5y": 1900,
    }.get(period, 400)

    start = (
        pd.Timestamp.now()
        - pd.Timedelta(days=days)
    ).strftime("%Y%m%d")

    try:
        df = _fetch_yahoo_chart(
            ticker,
            period=period,
            interval=interval,
        )

    except Exception as exc:
        raise _friendly_not_found(ticker, exc) from exc

    if df.empty:
        raise TickerNotFoundError(
            f"No historical data found for ticker '{ticker}'."
        )

    points = []

    for _, row in df.iterrows():

        points.append(
            HistoricalPricePoint(
                date=row["Date"].strftime("%Y-%m-%d"),
                open=round(float(row["Open"]), 2),
                high=round(float(row["High"]), 2),
                low=round(float(row["Low"]), 2),
                close=round(float(row["Close"]), 2),
                volume=int(row["Volume"]),
            )
        )

    result = HistoricalPrices(
        ticker=ticker,
        period=period,
        interval=interval,
        points=points,
    )

    cache.set(
        key,
        result,
        ttl_seconds=3600,
    )

    return result


# ---------------------------------------------------------------------------
# Company profile
# ---------------------------------------------------------------------------

def get_company_profile(ticker: str) -> CompanyProfile:

    ticker = ticker.upper().strip()

    key = cache_key(
        "profile",
        ticker,
    )

    if cached := cache.get(key):
        return cached

    log.info(
        f"[TOOL] get_company_profile({ticker})"
    )

    try:
        company = _get_sec_company(ticker)

    except Exception as exc:
        raise _friendly_not_found(
            ticker,
            exc,
        ) from exc

    result = CompanyProfile(
        ticker=ticker,
        name=company.get("name") or ticker,
        sector=None,
        industry=None,
        description=None,
        website=None,
        employees=None,
    )

    cache.set(
        key,
        result,
        ttl_seconds=6 * 3600,
    )

    return result

def get_market_dataframe(
    ticker: str,
    period: str = "2y",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Internal helper for analytics modules.

    Returns raw OHLCV data as a pandas DataFrame.
    Uses the same cached/free market-data source as the public
    stock-data functions.
    """
    ticker = ticker.upper().strip()

    return _fetch_yahoo_chart(
        ticker,
        period=period,
        interval=interval,
    )