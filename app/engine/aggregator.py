"""Blend pillar scores into a per-horizon verdict with confidence.

Improvements (v2):
  - Strong Buy requires confidence ≥ STRONG_BUY_THRESHOLD (85%); otherwise
    downgraded to Buy.
  - Data-freshness penalty: if fundamental data is stale (>3 days),
    confidence is reduced by up to 15 points.
  - Sector-momentum adjustment is applied externally via
    apply_sector_adjustment() after aggregate() returns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.engine.zones import score_to_zone
from app.schemas import Verdict

# Pillar weights per horizon: (fundamental, technical, news)
HORIZON_BLEND = {
    "short":  (0.20, 0.55, 0.25),
    "medium": (0.40, 0.40, 0.20),
    "long":   (0.55, 0.30, 0.15),
}

CONFIDENCE_THRESHOLD = 60.0   # minimum to emit a directional verdict
STRONG_BUY_THRESHOLD = 85.0   # minimum confidence to keep "Strong Buy" label
STRONG_SELL_THRESHOLD = 85.0  # minimum confidence to keep "Strong Sell" label

# Staleness penalty: per calendar day beyond 3-day grace period (capped at 15)
FRESHNESS_PENALTY_PER_DAY = 5.0
FRESHNESS_GRACE_DAYS = 3
MAX_FRESHNESS_PENALTY = 15.0


@dataclass
class PillarInput:
    score: float
    present: bool  # whether we had enough data to trust this pillar


def _sign(x: float) -> int:
    if x > 8:
        return 1
    if x < -8:
        return -1
    return 0


def _agreement(signs: List[int], present_flags: List[bool]) -> float:
    """Fraction of *present* pillars that agree with the dominant direction.

    Pillars that are absent (present=False) are excluded so missing news
    doesn't artificially tank agreement.
    """
    active_signs = [s for s, p in zip(signs, present_flags) if p]
    if not active_signs:
        return 0.0
    nonzero = [s for s in active_signs if s != 0]
    if not nonzero:
        return 0.3  # all flat
    pos = sum(1 for s in nonzero if s > 0)
    neg = sum(1 for s in nonzero if s < 0)
    dominant = max(pos, neg)
    return dominant / len(active_signs)


def _freshness_penalty(data_freshness_days: int) -> float:
    """Return a confidence penalty (positive number to subtract) for stale data."""
    excess = max(0, data_freshness_days - FRESHNESS_GRACE_DAYS)
    return min(MAX_FRESHNESS_PENALTY, excess * FRESHNESS_PENALTY_PER_DAY)


def _enforce_extreme_verdict_floor(verdict: Verdict, confidence: float) -> Verdict:
    """Downgrade Strong Buy/Sell if confidence doesn't meet the higher bar."""
    if verdict == "Strong Buy" and confidence < STRONG_BUY_THRESHOLD:
        return "Buy"
    if verdict == "Strong Sell" and confidence < STRONG_SELL_THRESHOLD:
        return "Sell"
    return verdict


@dataclass
class HorizonResult:
    score: float
    confidence: float
    verdict: Verdict
    freshness_penalty: float = 0.0


def aggregate(
    fundamental: PillarInput,
    technical_by_horizon: Dict[str, PillarInput],
    news: PillarInput,
    data_freshness_days: int = 0,
) -> Tuple[str, HorizonResult, Dict[str, HorizonResult], str | None]:
    """Compute per-horizon results and pick the dominant horizon.

    Args:
        fundamental: Fundamental pillar score + presence flag.
        technical_by_horizon: Per-horizon technical pillar inputs.
        news: News sentiment pillar.
        data_freshness_days: Calendar days since last price data (for staleness penalty).

    Returns: (chosen_horizon, chosen_result, all_horizons, reason_if_neutral)
    """
    results: Dict[str, HorizonResult] = {}
    penalty = _freshness_penalty(data_freshness_days)

    for horizon, (wf, wt, wn) in HORIZON_BLEND.items():
        t = technical_by_horizon[horizon]

        # Re-weight when news is absent: redistribute its weight proportionally.
        if not news.present:
            wf2 = wf + wn * 0.3
            wt2 = wt + wn * 0.7
            wn2 = 0.0
        else:
            wf2, wt2, wn2 = wf, wt, wn

        final = wf2 * fundamental.score + wt2 * t.score + wn2 * news.score

        signs = [_sign(fundamental.score), _sign(t.score), _sign(news.score)]
        present_flags = [fundamental.present, t.present, news.present]
        agreement = _agreement(signs, present_flags)

        strength = min(1.0, abs(final) / 40.0)

        present_count = sum(1 for p in [fundamental, t, news] if p.present)
        data_quality = present_count / 3.0

        raw_confidence = 100 * (0.5 * agreement + 0.35 * strength + 0.15 * data_quality)
        # Apply data-freshness penalty
        confidence = max(0.0, min(100.0, raw_confidence - penalty))

        raw_verdict = score_to_zone(final) if confidence >= CONFIDENCE_THRESHOLD else "Neutral"
        verdict = _enforce_extreme_verdict_floor(raw_verdict, confidence)

        results[horizon] = HorizonResult(
            score=final,
            confidence=confidence,
            verdict=verdict,
            freshness_penalty=penalty,
        )

    # Pick the horizon with confidence >= threshold and largest |score|.
    # Tie-break: prefer longer horizon (more stable).
    horizon_order = ["long", "medium", "short"]
    qualified = [
        (h, results[h])
        for h in horizon_order
        if results[h].confidence >= CONFIDENCE_THRESHOLD
    ]
    if qualified:
        qualified.sort(
            key=lambda x: (abs(x[1].score), horizon_order.index(x[0]) * -1),
            reverse=True,
        )
        chosen_h, chosen = qualified[0]
        return chosen_h, chosen, results, None

    # No qualifier: return the highest-confidence horizon as Neutral with a reason.
    best_h = max(results, key=lambda h: results[h].confidence)
    reason = _explain_low_confidence(
        fundamental, technical_by_horizon[best_h], news, results[best_h], penalty
    )
    neutral = HorizonResult(
        score=results[best_h].score,
        confidence=results[best_h].confidence,
        verdict="Neutral",
        freshness_penalty=penalty,
    )
    return best_h, neutral, results, reason


def apply_sector_adjustment(
    result: HorizonResult,
    confidence_delta: float,
    sector_reason: Optional[str],
    existing_reason: Optional[str],
) -> Tuple[HorizonResult, Optional[str]]:
    """Apply sector-momentum confidence adjustment to a chosen HorizonResult.

    Returns updated (result, reason).
    """
    if confidence_delta == 0.0:
        return result, existing_reason

    new_conf = max(0.0, min(100.0, result.confidence + confidence_delta))

    # Re-derive verdict with updated confidence
    if new_conf < CONFIDENCE_THRESHOLD:
        new_verdict = "Neutral"
    else:
        new_verdict = _enforce_extreme_verdict_floor(result.verdict, new_conf)

    combined_reason = existing_reason
    if sector_reason:
        combined_reason = (
            f"{existing_reason} {sector_reason}" if existing_reason else sector_reason
        )

    updated = HorizonResult(
        score=result.score,
        confidence=new_conf,
        verdict=new_verdict,
        freshness_penalty=result.freshness_penalty,
    )
    return updated, combined_reason


def _explain_low_confidence(
    f: PillarInput,
    t: PillarInput,
    n: PillarInput,
    r: HorizonResult,
    penalty: float = 0.0,
) -> str:
    signs = {"fundamental": _sign(f.score), "technical": _sign(t.score), "news": _sign(n.score)}
    missing = [name for name, p in {"fundamental": f, "technical": t, "news": n}.items() if not p.present]

    pos = [k for k, v in signs.items() if v > 0]
    neg = [k for k, v in signs.items() if v < 0]

    parts = [f"Confidence {r.confidence:.0f}% < {CONFIDENCE_THRESHOLD:.0f}%."]
    if penalty > 0:
        parts.append(f"Data freshness penalty: -{penalty:.0f} pts.")
    if missing:
        parts.append(f"Insufficient data: {', '.join(missing)}.")
    if pos and neg:
        parts.append(f"Pillars disagree — bullish: {', '.join(pos)}; bearish: {', '.join(neg)}.")
    elif abs(r.score) < 15:
        parts.append("Signal magnitude too weak.")
    return " ".join(parts)
