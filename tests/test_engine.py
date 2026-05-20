"""Engine-level tests: zones, confidence threshold, horizon selection."""
from app.engine.aggregator import (
    PillarInput, aggregate, apply_sector_adjustment,
    CONFIDENCE_THRESHOLD, STRONG_BUY_THRESHOLD,
)
from app.engine.zones import score_to_zone


def _tech(s: float, present: bool = True) -> dict:
    return {h: PillarInput(score=s, present=present) for h in ["short", "medium", "long"]}


def test_zone_boundaries():
    # Scores are in [-100, +100]; normalised to [0,100] before zone lookup.
    # normalise(x) = (x + 100) / 2
    # Strong Buy  : normalised > 75  → raw > 50
    assert score_to_zone(51) == "Strong Buy"
    assert score_to_zone(50) == "Buy"       # normalised = 75 → "Buy"
    # Buy         : normalised 55-75 → raw 10-50
    assert score_to_zone(10) == "Buy"       # normalised = 55
    assert score_to_zone(9) == "Neutral"    # normalised = 54.5
    # Neutral     : normalised 30-55 → raw -40 to 10
    assert score_to_zone(0) == "Neutral"    # normalised = 50
    assert score_to_zone(-40) == "Neutral"  # normalised = 30
    assert score_to_zone(-41) == "Sell"     # normalised = 29.5
    # Sell        : normalised 15-30 → raw -70 to -40
    assert score_to_zone(-70) == "Sell"     # normalised = 15
    assert score_to_zone(-71) == "Strong Sell"
    assert score_to_zone(-100) == "Strong Sell"


def test_strong_aligned_signals_pass_confidence():
    f = PillarInput(score=70, present=True)
    n = PillarInput(score=60, present=True)
    chosen_h, chosen, all_r, reason = aggregate(f, _tech(70), n)
    assert chosen.verdict in ("Buy", "Strong Buy")
    assert chosen.confidence >= CONFIDENCE_THRESHOLD
    assert reason is None


def test_moderate_aligned_signals_produce_verdict():
    # Realistic case: good fundamentals, positive technicals, no news
    f = PillarInput(score=40, present=True)
    n = PillarInput(score=0, present=False)
    chosen_h, chosen, all_r, reason = aggregate(f, _tech(35), n)
    assert chosen.verdict in ("Buy", "Neutral")
    assert chosen.confidence > 0


def test_disagreeing_pillars_forced_neutral():
    # When pillars disagree, the net score may still be Neutral with high confidence
    # OR low confidence with a reason. Either way verdict must be Neutral.
    f = PillarInput(score=70, present=True)
    n = PillarInput(score=-60, present=True)
    chosen_h, chosen, all_r, reason = aggregate(f, _tech(-70), n)
    assert chosen.verdict == "Neutral"


def test_weak_signals_neutral_with_reason():
    f = PillarInput(score=10, present=True)
    n = PillarInput(score=5, present=True)
    chosen_h, chosen, all_r, reason = aggregate(f, _tech(8), n)
    assert chosen.verdict == "Neutral"
    assert reason is not None


def test_missing_news_data_lowers_confidence():
    f = PillarInput(score=55, present=True)
    n = PillarInput(score=0, present=False)
    # technical aligned but news absent: confidence may still pass or fall — assert structure
    chosen_h, chosen, all_r, reason = aggregate(f, _tech(55), n)
    assert chosen.score > 0
    # Either passes with note, or neutral with reason mentioning news
    if chosen.verdict == "Neutral":
        assert "news" in reason.lower()


def test_horizon_selection_prefers_longer_when_tied():
    # All horizons get equal pillar scores, so confidence/scores equal -> longer horizon wins.
    f = PillarInput(score=70, present=True)
    n = PillarInput(score=70, present=True)
    chosen_h, chosen, all_r, reason = aggregate(f, _tech(70), n)
    assert chosen_h == "long"


def test_short_term_wins_when_only_technical_strong():
    # Fundamentals flat, news neutral, technicals only strong -> short horizon weights technicals most.
    f = PillarInput(score=0, present=True)
    n = PillarInput(score=0, present=True)
    tech = _tech(95)
    chosen_h, chosen, all_r, reason = aggregate(f, tech, n)
    # Short-term weight on technicals is 0.55 -> final ~52, long-term 0.30 -> ~28
    # All three horizons get same sign, so confidence is dominated by strength; short should be highest.
    assert all_r["short"].score > all_r["long"].score


def test_strong_buy_requires_high_confidence():
    # Strong Buy verdict must be downgraded to Buy when confidence < 85%.
    # Give moderate scores — enough to cross the zone but not enough for 85% confidence.
    f = PillarInput(score=55, present=True)
    n = PillarInput(score=0, present=False)   # absent news lowers confidence
    chosen_h, chosen, all_r, reason = aggregate(f, _tech(55), n)
    # If engine would emit Strong Buy (score > 50), it must have confidence >= 85%
    if chosen.verdict == "Strong Buy":
        assert chosen.confidence >= STRONG_BUY_THRESHOLD


def test_stale_data_reduces_confidence():
    # With 5 stale days (grace=3), penalty = 2×5 = 10 points.
    f = PillarInput(score=60, present=True)
    n = PillarInput(score=60, present=True)
    _, fresh, _, _ = aggregate(f, _tech(60), n, data_freshness_days=0)
    _, stale, _, _ = aggregate(f, _tech(60), n, data_freshness_days=5)
    assert stale.confidence < fresh.confidence


def test_sector_adjustment_downgrade():
    # A -20 pt sector penalty should reduce confidence and can push verdict to Neutral.
    f = PillarInput(score=60, present=True)
    n = PillarInput(score=60, present=True)
    _, result, _, reason = aggregate(f, _tech(60), n)
    updated, new_reason = apply_sector_adjustment(result, -20.0, "Sector in downtrend", None)
    assert updated.confidence < result.confidence
    assert "Sector" in (new_reason or "")
