"""Resolve a human-entered stock name/symbol to a yfinance ticker for Indian markets."""
from __future__ import annotations

import re
from functools import lru_cache

import yfinance as yf

COMMON_ALIASES = {
    "reliance": "RELIANCE.NS",
    "ril": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "infy": "INFY.NS",
    "infosys": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS",
    "hdfcbank": "HDFCBANK.NS",
    "icici bank": "ICICIBANK.NS",
    "icicibank": "ICICIBANK.NS",
    "sbi": "SBIN.NS",
    "state bank of india": "SBIN.NS",
    "axis bank": "AXISBANK.NS",
    "kotak bank": "KOTAKBANK.NS",
    "lt": "LT.NS",
    "l&t": "LT.NS",
    "larsen": "LT.NS",
    "itc": "ITC.NS",
    "hul": "HINDUNILVR.NS",
    "hindustan unilever": "HINDUNILVR.NS",
    "bajaj finance": "BAJFINANCE.NS",
    "bajfinance": "BAJFINANCE.NS",
    "asian paints": "ASIANPAINT.NS",
    "maruti": "MARUTI.NS",
    "tata motors": "TATAMOTORS.NS",
    "tata steel": "TATASTEEL.NS",
    "adani ports": "ADANIPORTS.NS",
    "wipro": "WIPRO.NS",
    "ongc": "ONGC.NS",
    "ntpc": "NTPC.NS",
    "powergrid": "POWERGRID.NS",
    "yes bank": "YESBANK.NS",
    "yesbank": "YESBANK.NS",
}


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


@lru_cache(maxsize=256)
def _validate_ticker(symbol: str) -> bool:
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:
        return False
    return bool(info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose"))


def resolve_ticker(query: str) -> str:
    """Resolve user input to an NSE/BSE yfinance ticker.

    Strategy:
      1. If input already has .NS / .BO suffix, use as-is.
      2. Check common alias table.
      3. Try uppercased + .NS, then + .BO.
      4. Raise ValueError if nothing validates.
    """
    if not query or not query.strip():
        raise ValueError("Empty stock query")

    q = _normalize(query)
    raw = query.strip().upper()

    if raw.endswith(".NS") or raw.endswith(".BO"):
        if _validate_ticker(raw):
            return raw
        raise ValueError(f"Ticker {raw} not found")

    if q in COMMON_ALIASES:
        return COMMON_ALIASES[q]

    candidate = raw.replace(" ", "") + ".NS"
    if _validate_ticker(candidate):
        return candidate

    candidate_bo = raw.replace(" ", "") + ".BO"
    if _validate_ticker(candidate_bo):
        return candidate_bo

    raise ValueError(f"Could not resolve '{query}' to an Indian stock ticker")
