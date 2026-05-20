#!/usr/bin/env python3
"""Debug script to test VEDL ticker resolution."""

import yfinance as yf
from app.resolver import resolve_ticker, _validate_ticker, COMMON_ALIASES

print("=" * 60)
print("DEBUGGING VEDL TICKER RESOLUTION")
print("=" * 60)

# Test 1: Direct yfinance API call
print("\n1. Testing yfinance directly for VEDL.NS:")
ticker = yf.Ticker("VEDL.NS")
print(f"   - Ticker object created: {ticker}")
print(f"   - Info type: {type(ticker.info)}")
print(f"   - Info content: {ticker.info}")
print(f"   - Info keys: {list(ticker.info.keys())[:10]}...")  # First 10 keys

# Check specific fields
if ticker.info:
    print(f"   - regularMarketPrice: {ticker.info.get('regularMarketPrice')}")
    print(f"   - currentPrice: {ticker.info.get('currentPrice')}")
    print(f"   - previousClose: {ticker.info.get('previousClose')}")
    print(f"   - has valid price data: {bool(ticker.info.get('regularMarketPrice') or ticker.info.get('currentPrice') or ticker.info.get('previousClose'))}")

# Test 2: Test _validate_ticker function
print("\n2. Testing _validate_ticker() function:")
result = _validate_ticker("VEDL.NS")
print(f"   - _validate_ticker('VEDL.NS') = {result}")

# Clear cache for next test
print("\n3. Clearing validator cache and retesting:")
_validate_ticker.cache_clear()
result2 = _validate_ticker("VEDL.NS")
print(f"   - _validate_ticker('VEDL.NS') after cache clear = {result2}")

# Test 4: Test resolve_ticker function
print("\n4. Testing resolve_ticker() function:")
try:
    resolved = resolve_ticker("VEDL")
    print(f"   - resolve_ticker('VEDL') = {resolved}")
except Exception as e:
    print(f"   - resolve_ticker('VEDL') FAILED with: {type(e).__name__}: {e}")

# Test 5: Check if VEDL is in NIFTY_100
print("\n5. Checking NIFTY_100 list:")
from app.main import NIFTY_100
print(f"   - Total stocks in NIFTY_100: {len(NIFTY_100)}")
print(f"   - Is VEDL in NIFTY_100? {('VEDL' in NIFTY_100)}")
print(f"   - Is VEDL.NS in NIFTY_100? {('VEDL.NS' in NIFTY_100)}")

# Test 6: Check common aliases
print("\n6. Checking COMMON_ALIASES:")
print(f"   - Is 'vedl' in COMMON_ALIASES? {('vedl' in COMMON_ALIASES)}")
if 'vedl' in COMMON_ALIASES:
    print(f"   - COMMON_ALIASES['vedl'] = {COMMON_ALIASES['vedl']}")

print("\n" + "=" * 60)
