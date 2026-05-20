"""Signal-level tests using synthetic inputs (no network)."""
import numpy as np
import pandas as pd
import pytest

from app.data.fundamentals import Fundamentals
from app.signals.fundamental import score_fundamentals
from app.signals.technical import score_technical


def _synthetic_uptrend(n: int = 260, start: float = 100.0) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    close = np.linspace(start, start * 1.5, n) + np.sin(np.arange(n) / 10) * 2
    return pd.DataFrame({
        "open": close,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": np.full(n, 100000),
    }, index=idx)


def _synthetic_downtrend(n: int = 260, start: float = 100.0) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    close = np.linspace(start, start * 0.7, n) + np.sin(np.arange(n) / 10) * 2
    return pd.DataFrame({
        "open": close,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": np.full(n, 100000),
    }, index=idx)


def test_fundamentals_strong_buy_profile():
    f = Fundamentals(pe=12, pb=1.2, roe=0.22, debt_to_equity=0.3, earnings_growth=0.25, revenue_growth=0.18)
    score, highlights, extras = score_fundamentals(f)
    assert score > 50
    assert extras["factors_present"] == 6


def test_fundamentals_weak_profile():
    f = Fundamentals(pe=80, pb=8, roe=-0.05, debt_to_equity=3, earnings_growth=-0.2, revenue_growth=-0.1)
    score, highlights, extras = score_fundamentals(f)
    assert score < -40


def test_fundamentals_missing_data_returns_zero():
    score, _, extras = score_fundamentals(Fundamentals())
    assert score == 0
    assert extras["factors_present"] == 0


def test_technical_uptrend_is_positive_long_horizon():
    df = _synthetic_uptrend()
    by_h = score_technical(df)
    assert by_h["long"][0] > 0
    assert by_h["medium"][0] > 0


def test_technical_downtrend_is_negative_long_horizon():
    df = _synthetic_downtrend()
    by_h = score_technical(df)
    assert by_h["long"][0] < 0
