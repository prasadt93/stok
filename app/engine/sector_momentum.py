"""Sector momentum filter.

Computes the median 1-month price return for a set of peer stocks in the same
sector and returns a confidence penalty when the sector is in a broad downtrend.

Penalty logic:
  sector_return < -10% → penalty = 20 points
  sector_return < -5%  → penalty = 10 points
  sector_return > +10% → bonus  = +5 points (mild tailwind)
  otherwise            → 0

The penalty is applied AFTER the base confidence is computed and caps at 20.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import yfinance as yf

# Sector → representative NSE peer tickers (5-6 per sector, liquid names)
SECTOR_PEERS: Dict[str, List[str]] = {
    "Technology": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
    "Financial Services": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS", "GAIL.NS"],
    "Basic Materials": ["TATASTEEL.NS", "JSWSTEEL.NS", "VEDL.NS", "HINDALCO.NS", "COALINDIA.NS"],
    "Consumer Cyclical": ["MARUTI.NS", "BAJAJFINSV.NS", "HEROMOTOCORP.NS", "MOTHERSON.NS", "M&M.NS"],
    "Consumer Defensive": ["ITC.NS", "NESTLEIND.NS", "HINDUNILVR.NS", "BRITANNIA.NS", "DABUR.NS"],
    "Healthcare": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "LUPIN.NS", "DIVISLAB.NS"],
    "Industrials": ["LT.NS", "BHARATFORG.NS", "SIEMENS.NS", "ABB.NS", "CUMMINSIND.NS"],
    "Communication Services": ["BHARTIARTL.NS", "INDIGO.NS"],
    "Utilities": ["NTPC.NS", "POWERGRID.NS", "ADANIGREEN.NS"],
    "Real Estate": ["GODREJPROP.NS", "DLF.NS", "OBEROIRLTY.NS"],
}


def _median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return (s[mid - 1] + s[mid]) / 2 if n % 2 == 0 else s[mid]


def sector_confidence_adjustment(sector: Optional[str]) -> tuple[float, str | None]:
    """Return (confidence_delta, reason_or_None).

    confidence_delta is negative (penalty) or positive (bonus).
    """
    if not sector:
        return 0.0, None

    peers = SECTOR_PEERS.get(sector)
    if not peers:
        return 0.0, None

    returns: List[float] = []
    for ticker in peers:
        try:
            hist = yf.Ticker(ticker).history(period="1mo", auto_adjust=True)
            if len(hist) >= 10:
                ret = (hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0] * 100
                returns.append(ret)
        except Exception:
            continue

    median_ret = _median(returns)
    if median_ret is None:
        return 0.0, None

    if median_ret < -10:
        return -20.0, f"Sector '{sector}' in broad downtrend ({median_ret:.1f}% 1m median)"
    if median_ret < -5:
        return -10.0, f"Sector '{sector}' weak ({median_ret:.1f}% 1m median)"
    if median_ret > 10:
        return +5.0, None  # quiet tailwind, no noise in reason
    return 0.0, None
