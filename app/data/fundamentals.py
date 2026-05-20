"""Fundamental data fetcher (yfinance .info, with defensive defaults).

Also computes a data_freshness_days field: the number of calendar days
between today and the last trading date in yfinance's price history.
When fundamentals are stale (>3 trading days old), the aggregator can
reduce confidence to avoid acting on lagged data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf


@dataclass
class Fundamentals:
    pe: Optional[float] = None
    pb: Optional[float] = None
    roe: Optional[float] = None              # fraction, e.g. 0.18 = 18%
    debt_to_equity: Optional[float] = None   # normalised ratio
    earnings_growth: Optional[float] = None  # YoY, fraction
    revenue_growth: Optional[float] = None   # YoY, fraction
    sector: Optional[str] = None
    market_cap: Optional[float] = None
    dividend_yield: Optional[float] = None
    raw: dict = field(default_factory=dict)
    # How many calendar days since the last price data point (freshness proxy)
    data_freshness_days: int = 0

    def is_present(self) -> bool:
        return any(v is not None for v in [self.pe, self.pb, self.roe, self.debt_to_equity])

    @property
    def is_stale(self) -> bool:
        """True when price data is more than 3 calendar days old."""
        return self.data_freshness_days > 3


def fetch_fundamentals(ticker: str) -> Fundamentals:
    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info or {}
    except Exception:
        info = {}
        yf_ticker = None

    # --- Debt/Equity normalisation ---
    de_raw = info.get("debtToEquity")
    # yfinance returns D/E as a percentage (e.g. 45.2 = 0.452). Normalise.
    de = (de_raw / 100.0) if isinstance(de_raw, (int, float)) and de_raw and de_raw > 5 else de_raw

    # --- Data freshness ---
    freshness_days = 0
    try:
        hist = yf_ticker.history(period="5d", auto_adjust=True)
        if not hist.empty:
            last_date = hist.index[-1]
            # Make timezone-aware for comparison
            if hasattr(last_date, "tzinfo") and last_date.tzinfo is None:
                last_date = last_date.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            freshness_days = max(0, (now - last_date).days)
    except Exception:
        freshness_days = 0

    return Fundamentals(
        pe=info.get("trailingPE") or info.get("forwardPE"),
        pb=info.get("priceToBook"),
        roe=info.get("returnOnEquity"),
        debt_to_equity=de,
        earnings_growth=info.get("earningsGrowth") or info.get("earningsQuarterlyGrowth"),
        revenue_growth=info.get("revenueGrowth"),
        sector=info.get("sector"),
        market_cap=info.get("marketCap"),
        dividend_yield=info.get("dividendYield"),
        raw=info,
        data_freshness_days=freshness_days,
    )
