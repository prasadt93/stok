#!/usr/bin/env python3
"""Debug script to test the full recommend function for VEDL."""

import traceback
from app.service import recommend

print("=" * 60)
print("TESTING FULL RECOMMEND FUNCTION FOR VEDL")
print("=" * 60)

try:
    result = recommend("VEDL")
    print("\nSUCCESS! Recommendation result:")
    print(f"  Ticker: {result.ticker}")
    print(f"  Verdict: {result.verdict}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Final Score: {result.final_score}")
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
    print("\nFull traceback:")
    traceback.print_exc()

print("\n" + "=" * 60)
