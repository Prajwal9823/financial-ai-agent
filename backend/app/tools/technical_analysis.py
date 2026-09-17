"""
TOOL: calculate_technical_indicators

All math here is plain pandas/numpy — deliberately NOT delegated to the
LLM (rule #11). Each function operates on a close-price (and high/low
where needed) pandas Series and returns a plain float, so this module has
zero dependency on the web framework or the LLM layer and is easy to unit
test in isolation (see tests/test_technical_analysis.py).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.cache import cache, cache_key
from app.core.logging_config import get_logger
from app.core.rate_limiter import with_retry
from app.models.schemas import TechnicalIndicators
from app.tools.stock_data import (
    TickerNotFoundError,
    _friendly_not_found,
    get_market_dataframe,
)

log = get_logger("tools.technical_analysis")


# ---------------------------------------------------------------------------
# Pure math helpers (unit-testable, no I/O)
# ---------------------------------------------------------------------------

def sma(series: pd.Series, window: int) -> float | None:
    if len(series) < window:
        return None
    return round(float(series.rolling(window).mean().iloc[-1]), 2)


def ema(series: pd.Series, span: int) -> float | None:
    if len(series) < span:
        return None
    return round(float(series.ewm(span=span, adjust=False).mean().iloc[-1]), 2)


def macd(series: pd.Series) -> tuple[float | None, float | None, str | None]:
    if len(series) < 26:
        return None, None, None
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_val = round(float(macd_line.iloc[-1]), 3)
    signal_val = round(float(signal_line.iloc[-1]), 3)
    trend = "Bullish" if macd_val > signal_val else "Bearish" if macd_val < signal_val else "Neutral"
    return macd_val, signal_val, trend


def rsi(series: pd.Series, window: int = 14) -> float | None:
    if len(series) < window + 1:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean().iloc[-1]
    avg_loss = loss.rolling(window).mean().iloc[-1]

    if pd.isna(avg_gain) or pd.isna(avg_loss):
        return None
    if avg_loss == 0:
        # No losses in the window: max momentum (100) if there were gains,
        # otherwise a genuinely flat series -> neutral midpoint (50), not
        # "undefined" (avoids the NaN-from-division-by-zero the old
        # implementation silently produced here).
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    return round(float(100 - (100 / (1 + rs))), 2)


def stochastic_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> tuple[float | None, float | None]:
    if len(close) < window:
        return None, None
    lowest_low = low.rolling(window).min()
    highest_high = high.rolling(window).max()
    denom = (highest_high - lowest_low).replace(0, np.nan)
    k = 100 * (close - lowest_low) / denom
    d = k.rolling(3).mean()
    k_val, d_val = k.iloc[-1], d.iloc[-1]
    return (
        round(float(k_val), 2) if pd.notna(k_val) else None,
        round(float(d_val), 2) if pd.notna(d_val) else None,
    )


def bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0) -> tuple[float | None, float | None]:
    if len(series) < window:
        return None, None
    rolling_mean = series.rolling(window).mean()
    rolling_std = series.rolling(window).std()
    upper = rolling_mean + num_std * rolling_std
    lower = rolling_mean - num_std * rolling_std
    return round(float(upper.iloc[-1]), 2), round(float(lower.iloc[-1]), 2)


def historical_volatility(series: pd.Series, trading_days: int = 252) -> float | None:
    if len(series) < 2:
        return None
    log_returns = np.log(series / series.shift(1)).dropna()
    if log_returns.empty:
        return None
    return round(float(log_returns.std() * np.sqrt(trading_days) * 100), 2)  # annualized, in %


def max_drawdown(series: pd.Series) -> float | None:
    if series.empty:
        return None
    cumulative_max = series.cummax()
    drawdown = (series - cumulative_max) / cumulative_max
    return round(float(drawdown.min() * 100), 2)  # negative %, e.g. -23.5


def period_return(series: pd.Series, periods_back: int) -> float | None:
    if len(series) <= periods_back:
        return None
    start = series.iloc[-1 - periods_back]
    end = series.iloc[-1]
    if start == 0:
        return None
    return round(float((end - start) / start * 100), 2)


# ---------------------------------------------------------------------------
# Orchestrator — fetches data once, computes every indicator from it
# ---------------------------------------------------------------------------

# Rough trading-day offsets used for the "return over N" figures.
_RETURN_WINDOWS = {"return_1d": 1, "return_1w": 5, "return_1m": 21, "return_3m": 63, "return_1y": 252}


@with_retry()

def _fetch_2y_history(ticker: str):
    return get_market_dataframe(
        ticker,
        period="2y",
        interval="1d",
    )


def calculate_technical_indicators(ticker: str) -> TechnicalIndicators:
    key = cache_key("technicals", ticker)
    if cached := cache.get(key):
        return cached

    log.info(f"[TOOL] calculate_technical_indicators({ticker})")
    try:
        df = _fetch_2y_history(ticker)  # 2y gives enough history for 200D SMA + 1Y return
    except Exception as exc:  # noqa: BLE001 - yfinance raises raw errors for both bad tickers and rate limits
        raise _friendly_not_found(ticker, exc) from exc

    if df.empty:
        raise TickerNotFoundError(f"No price history available to compute indicators for '{ticker}'.")

    close, high, low = df["Close"], df["High"], df["Low"]
    macd_val, signal_val, trend = macd(close)
    stoch_k, stoch_d = stochastic_oscillator(high, low, close)
    boll_upper, boll_lower = bollinger_bands(close)

    result = TechnicalIndicators(
        ticker=ticker.upper(),
        sma_50=sma(close, 50),
        sma_200=sma(close, 200),
        ema_20=ema(close, 20),
        macd=macd_val,
        macd_signal=signal_val,
        macd_trend=trend,
        rsi_14=rsi(close),
        stochastic_k=stoch_k,
        stochastic_d=stoch_d,
        bollinger_upper=boll_upper,
        bollinger_lower=boll_lower,
        historical_volatility=historical_volatility(close),
        max_drawdown=max_drawdown(close),
        return_1d=period_return(close, _RETURN_WINDOWS["return_1d"]),
        return_1w=period_return(close, _RETURN_WINDOWS["return_1w"]),
        return_1m=period_return(close, _RETURN_WINDOWS["return_1m"]),
        return_3m=period_return(close, _RETURN_WINDOWS["return_3m"]),
        return_1y=period_return(close, _RETURN_WINDOWS["return_1y"]),
    )
    cache.set(key, result, ttl_seconds=900)
    return result
