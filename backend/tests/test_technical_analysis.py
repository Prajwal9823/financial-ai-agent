"""
Unit tests for the deterministic indicator math in technical_analysis.py.

These use hand-built pandas Series (no network calls) so they run
instantly and don't depend on live market data being available.
"""
import numpy as np
import pandas as pd
import pytest

from app.tools.technical_analysis import (
    bollinger_bands,
    ema,
    historical_volatility,
    macd,
    max_drawdown,
    period_return,
    rsi,
    sma,
    stochastic_oscillator,
)


@pytest.fixture
def rising_prices() -> pd.Series:
    # Compounding (accelerating) growth, not a straight line. A perfectly
    # linear ramp has *constant* daily increments, so its MACD line and
    # signal line both converge to the same constant after enough days —
    # correctly reading as "Neutral" once fully converged. Compounding
    # growth keeps accelerating, which is what actually sustains a
    # persistent MACD > signal (bullish) reading, and still gives us the
    # strictly-increasing series the RSI-near-100 test needs.
    return pd.Series(100 * (1.004 ** np.arange(260)))


@pytest.fixture
def flat_prices() -> pd.Series:
    return pd.Series([100.0] * 60)


def test_sma_basic():
    series = pd.Series([1, 2, 3, 4, 5])
    assert sma(series, 5) == 3.0
    assert sma(series, 10) is None  # not enough data


def test_ema_matches_pandas_ewm():
    series = pd.Series(range(1, 31), dtype=float)
    expected = round(float(series.ewm(span=20, adjust=False).mean().iloc[-1]), 2)
    assert ema(series, 20) == expected


def test_rsi_all_gains_is_near_100(rising_prices):
    value = rsi(rising_prices)
    assert value is not None
    assert value > 95


def test_rsi_flat_series_is_neutral(flat_prices):
    # Zero price movement -> zero gains AND zero losses -> neutral midpoint.
    assert rsi(flat_prices) == 50.0


def test_rsi_all_losses_is_near_zero():
    falling = pd.Series(np.linspace(200, 100, 260))
    value = rsi(falling)
    assert value is not None
    assert value < 5


def test_macd_bullish_on_uptrend(rising_prices):
    macd_val, signal_val, trend = macd(rising_prices)
    assert trend == "Bullish"
    assert macd_val > signal_val


def test_bollinger_bands_bracket_the_mean():
    series = pd.Series(np.random.default_rng(42).normal(100, 5, 40))
    upper, lower = bollinger_bands(series)
    assert lower < series.iloc[-20:].mean() < upper


def test_max_drawdown_is_negative_or_zero():
    series = pd.Series([100, 120, 90, 110, 80, 130])
    dd = max_drawdown(series)
    assert dd <= 0
    # Drop from peak 120 to trough 80 = -33.33%
    assert dd == pytest.approx(-33.33, abs=0.1)


def test_period_return_basic():
    series = pd.Series([100, 105, 110, 121])
    assert period_return(series, 1) == pytest.approx(10.0, abs=0.01)
    assert period_return(series, 10) is None  # not enough history


def test_historical_volatility_is_nonnegative(rising_prices):
    vol = historical_volatility(rising_prices)
    assert vol is not None
    assert vol >= 0


def test_stochastic_oscillator_bounds():
    high = pd.Series(np.linspace(105, 205, 30))
    low = pd.Series(np.linspace(95, 195, 30))
    close = pd.Series(np.linspace(100, 200, 30))
    k, d = stochastic_oscillator(high, low, close)
    assert 0 <= k <= 100
    assert 0 <= d <= 100
