"""Resolve a human-entered stock name/symbol to a yfinance ticker for Indian markets."""
from __future__ import annotations

import re

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
    # Common full names
    "bajaj auto": "BAJAJ-AUTO.NS",
    "mahindra": "M&M.NS",
    "m&m": "M&M.NS",
    "hero motocorp": "HEROMOTOCO.NS",
    "hero": "HEROMOTOCO.NS",
    "sun pharma": "SUNPHARMA.NS",
    "sunpharma": "SUNPHARMA.NS",
    "dr reddy": "DRREDDY.NS",
    "drreddy": "DRREDDY.NS",
    "cipla": "CIPLA.NS",
    "hcl tech": "HCLTECH.NS",
    "hcltech": "HCLTECH.NS",
    "tech mahindra": "TECHM.NS",
    "techm": "TECHM.NS",
    "ultratech cement": "ULTRACEMCO.NS",
    "ultracemco": "ULTRACEMCO.NS",
    "titan": "TITAN.NS",
    "nestle": "NESTLEIND.NS",
    "nestleind": "NESTLEIND.NS",
    "zomato": "ZOMATO.NS",
    "paytm": "PAYTM.NS",
    "dmart": "DMART.NS",
    "trent": "TRENT.NS",
    "jsw steel": "JSWSTEEL.NS",
    "jswsteel": "JSWSTEEL.NS",
    "hindalco": "HINDALCO.NS",
    "coal india": "COALINDIA.NS",
    "coalindia": "COALINDIA.NS",
    "bpcl": "BPCL.NS",
    "grasim": "GRASIM.NS",
}


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


# Pattern for valid NSE/BSE ticker symbols (letters, digits, &, -)
_TICKER_RE = re.compile(r"^[A-Z0-9&\-]{1,20}$")


def resolve_ticker(query: str) -> str:
    """Resolve user input to an NSE/BSE yfinance ticker.

    Strategy:
      1. If input already has .NS / .BO suffix, use as-is.
      2. Check common alias table.
      3. For any clean symbol (letters/digits/&/-), default to .NS.
         The data fetching layer will raise ValueError if the ticker
         has no price history, producing a clean 404 error.
      4. Raise ValueError for obviously invalid inputs.

    No yfinance API calls are made here — validation is handled
    implicitly by the price history fetch in service.py, avoiding
    rate-limit issues on the hosted server.
    """
    if not query or not query.strip():
        raise ValueError("Empty stock query")

    q = _normalize(query)
    raw = query.strip().upper()

    # Already has exchange suffix — use as-is
    if raw.endswith(".NS") or raw.endswith(".BO"):
        return raw

    # Known alias
    if q in COMMON_ALIASES:
        return COMMON_ALIASES[q]

    # Clean symbol — strip spaces (handles "HDFC BANK" → "HDFCBANK")
    clean = raw.replace(" ", "")
    if _TICKER_RE.match(clean):
        return clean + ".NS"  # Default to NSE; data layer catches invalid tickers

    raise ValueError(
        f"Could not resolve '{query}' to a valid stock symbol. "
        "Try the NSE ticker directly, e.g. 'VEDL', 'TCS', 'RELIANCE'."
    )
