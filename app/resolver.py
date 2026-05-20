"""Resolve a human-entered stock name/symbol to a yfinance ticker for Indian markets."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

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
    "vedanta": "VEDL.NS",
    "vedl": "VEDL.NS",
}

# Persistent cache for ticker validation (survives process restarts)
_CACHE_FILE = Path(__file__).parent.parent / ".ticker_cache.json"
_CACHE_TTL_HOURS = 24


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _load_cache() -> dict:
    """Load ticker validation cache from disk."""
    if not _CACHE_FILE.exists():
        return {}
    try:
        with open(_CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache: dict) -> None:
    """Save ticker validation cache to disk."""
    try:
        _CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except Exception:
        pass  # Silent fail if we can't write cache


def _is_cache_valid(timestamp: float) -> bool:
    """Check if a cache entry is still valid (not expired)."""
    age_hours = (datetime.now().timestamp() - timestamp) / 3600
    return age_hours < _CACHE_TTL_HOURS


@lru_cache(maxsize=256)
def _validate_ticker(symbol: str) -> bool:
    """Validate a ticker symbol using cached + yfinance validation.

    Uses persistent disk cache to avoid repeated yfinance calls.
    Falls back to yfinance if cache miss or cache expired.
    """
    cache = _load_cache()

    # Check if we have a valid cached result
    if symbol in cache:
        entry = cache[symbol]
        if _is_cache_valid(entry.get("timestamp", 0)):
            return entry.get("valid", False)

    # Validate via yfinance
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:
        valid = False
    else:
        valid = bool(info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose"))

    # Update cache
    cache[symbol] = {"valid": valid, "timestamp": datetime.now().timestamp()}
    _save_cache(cache)

    return valid


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
