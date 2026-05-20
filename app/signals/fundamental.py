"""Fundamental scoring -> [-100, +100] with highlight strings."""
from __future__ import annotations

from typing import List, Tuple

from app.data.fundamentals import Fundamentals


def _clip(x: float, lo: float = -100.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def score_fundamentals(f: Fundamentals) -> Tuple[float, List[str], dict]:
    score = 0.0
    highlights: List[str] = []
    factors_present = 0

    if f.pe is not None and f.pe > 0:
        factors_present += 1
        if f.pe < 15:
            score += 15; highlights.append(f"Low P/E {f.pe:.1f}")
        elif f.pe < 25:
            score += 5
        elif f.pe > 60:
            score -= 20; highlights.append(f"Very high P/E {f.pe:.1f}")
        elif f.pe > 40:
            score -= 10

    if f.pb is not None and f.pb > 0:
        factors_present += 1
        if f.pb < 1.5:
            score += 12; highlights.append(f"P/B {f.pb:.2f}")
        elif f.pb < 3:
            score += 4
        elif f.pb > 6:
            score -= 15
        elif f.pb > 4:
            score -= 6

    if f.roe is not None:
        factors_present += 1
        roe_pct = f.roe * 100
        if roe_pct > 18:
            score += 20; highlights.append(f"ROE {roe_pct:.1f}%")
        elif roe_pct > 12:
            score += 10
        elif roe_pct < 0:
            score -= 20; highlights.append(f"Negative ROE {roe_pct:.1f}%")
        elif roe_pct < 8:
            score -= 8

    if f.debt_to_equity is not None:
        factors_present += 1
        de = f.debt_to_equity
        if de < 0.5:
            score += 15; highlights.append(f"D/E {de:.2f}")
        elif de < 1.0:
            score += 5
        elif de < 2.0:
            score -= 8
        else:
            score -= 20; highlights.append(f"High D/E {de:.2f}")

    if f.earnings_growth is not None:
        factors_present += 1
        eg = f.earnings_growth * 100
        if eg > 20:
            score += 20; highlights.append(f"EPS growth {eg:.0f}%")
        elif eg > 10:
            score += 10
        elif eg < 0:
            score -= 15; highlights.append(f"EPS decline {eg:.0f}%")

    if f.revenue_growth is not None:
        factors_present += 1
        rg = f.revenue_growth * 100
        if rg > 15:
            score += 10
        elif rg < 0:
            score -= 10

    extras = {"factors_present": factors_present}
    return _clip(score), highlights, extras
