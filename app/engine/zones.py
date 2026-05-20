"""Map a final score [-100, +100] to a verdict zone.

Scores are normalised to [0, 100] before applying the user-defined thresholds
so that 0 (internally neutral) maps to 50, and the full bullish range maps to
the upper half of the [0, 100] scale.
"""
from __future__ import annotations

from app.schemas import Verdict


def _normalise(score: float) -> float:
    """Map [-100, +100] → [0, 100]."""
    return (max(-100.0, min(100.0, score)) + 100.0) / 2.0


def score_to_zone(score: float) -> Verdict:
    n = _normalise(score)
    if n > 75:
        return "Strong Buy"
    if n >= 55:
        return "Buy"
    if n >= 30:
        return "Neutral"
    if n >= 15:
        return "Sell"
    return "Strong Sell"
