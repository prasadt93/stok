"""Orchestrator that wires data fetch + signals + aggregation into a response."""
from __future__ import annotations

from datetime import datetime, timezone

from app.data.fundamentals import fetch_fundamentals
from app.data.news import fetch_news
from app.data.prices import fetch_history
from app.engine.aggregator import PillarInput, aggregate, apply_sector_adjustment
from app.engine.sector_momentum import sector_confidence_adjustment
from app.resolver import resolve_ticker
from app.schemas import (
    HORIZON_LABEL,
    HorizonScore,
    PillarBreakdown,
    RecommendationResponse,
)
from app.signals.fundamental import score_fundamentals
from app.signals.sentiment import score_news
from app.signals.technical import score_technical


def recommend(query: str) -> RecommendationResponse:
    ticker = resolve_ticker(query)

    # --- Data ---
    # If .NS has no data, try .BO (BSE) as fallback for BSE-only listed stocks
    try:
        price_df = fetch_history(ticker, period="1y")
    except ValueError:
        if ticker.endswith(".NS"):
            fallback = ticker[:-3] + ".BO"
            price_df = fetch_history(fallback, period="1y")  # raises if .BO also fails
            ticker = fallback
        else:
            raise
    fundamentals = fetch_fundamentals(ticker)
    news_items = fetch_news(
        ticker,
        query_hint=fundamentals.raw.get("shortName") if fundamentals.raw else None,
    )

    # --- Signals ---
    f_score, f_high, f_extras = score_fundamentals(fundamentals)
    tech_by_horizon = score_technical(price_df)   # {horizon: (score, highlights, extras)}
    n_score, n_high, n_extras = score_news(news_items)

    # --- Aggregation inputs ---
    f_input = PillarInput(
        score=f_score,
        present=fundamentals.is_present() and f_extras.get("factors_present", 0) >= 3,
    )
    tech_inputs = {
        h: PillarInput(score=tech_by_horizon[h][0], present=len(price_df) >= 50)
        for h in tech_by_horizon
    }
    n_input = PillarInput(score=n_score, present=n_extras.get("articles_used", 0) >= 2)

    # Pass data freshness so aggregator can penalise stale fundamental data
    chosen_h, chosen, all_results, reason = aggregate(
        f_input,
        tech_inputs,
        n_input,
        data_freshness_days=fundamentals.data_freshness_days,
    )

    # --- Sector momentum adjustment (applied after horizon selection) ---
    sector_delta, sector_reason = sector_confidence_adjustment(fundamentals.sector)
    chosen, reason = apply_sector_adjustment(chosen, sector_delta, sector_reason, reason)

    # --- Build response ---
    t_score, t_high, t_extras = tech_by_horizon[chosen_h]

    # Surface freshness warning in fundamental extras when data is stale
    f_extra_out = dict(f_extras)
    if fundamentals.data_freshness_days > 3:
        f_extra_out["data_freshness_warning"] = (
            f"Fundamental data may be {fundamentals.data_freshness_days}d old"
        )

    pillars = {
        "fundamental": PillarBreakdown(score=round(f_score, 1), highlights=f_high, extras=f_extra_out),
        "technical":   PillarBreakdown(score=round(t_score, 1), highlights=t_high, extras={"horizon": chosen_h}),
        "news":        PillarBreakdown(score=round(n_score, 1), highlights=n_high, extras=n_extras),
    }
    horizons = {
        h: HorizonScore(score=round(r.score, 1), confidence=round(r.confidence, 1), verdict=r.verdict)
        for h, r in all_results.items()
    }

    return RecommendationResponse(
        query=query,
        ticker=ticker,
        verdict=chosen.verdict,
        timeframe=HORIZON_LABEL[chosen_h],
        confidence=round(chosen.confidence, 1),
        final_score=round(chosen.score, 1),
        pillars=pillars,
        horizons=horizons,
        reason=reason,
        as_of=datetime.now(timezone.utc).isoformat(),
    )
