"""Price history fetcher (yfinance)."""
from __future__ import annotations

import pandas as pd
import yfinance as yf


def fetch_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Return daily OHLCV. Requires at least ~200 sessions for long-term signals."""
    df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    if df is None or df.empty:
        raise ValueError(f"No price history for {ticker}")
    df = df.rename(columns=str.lower)
    df.index = pd.to_datetime(df.index)
    return df[["open", "high", "low", "close", "volume"]].dropna()
