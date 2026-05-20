"""News sentiment via VADER, with recency decay."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List, Tuple

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.data.news import NewsItem

_analyzer = SentimentIntensityAnalyzer()
_HALF_LIFE_DAYS = 5.0


def _decay_weight(published: datetime, now: datetime) -> float:
    days = max(0.0, (now - published).total_seconds() / 86400.0)
    return 0.5 ** (days / _HALF_LIFE_DAYS)


def score_news(items: List[NewsItem]) -> Tuple[float, List[str], dict]:
    if not items:
        return 0.0, ["No recent news"], {"articles_used": 0}

    now = datetime.now(timezone.utc)
    weighted_sum = 0.0
    weight_total = 0.0
    top_pos = (None, -1.0)
    top_neg = (None, 1.0)

    for it in items:
        text = f"{it.title}. {it.summary}"
        compound = _analyzer.polarity_scores(text)["compound"]
        w = _decay_weight(it.published, now)
        weighted_sum += compound * w
        weight_total += w
        if compound > top_pos[1]:
            top_pos = (it.title, compound)
        if compound < top_neg[1]:
            top_neg = (it.title, compound)

    if weight_total == 0:
        return 0.0, ["Stale news"], {"articles_used": len(items)}

    score = (weighted_sum / weight_total) * 100
    score = max(-100.0, min(100.0, score))

    highlights = []
    if top_pos[0] and top_pos[1] > 0.2:
        highlights.append(f"+ {top_pos[0][:80]}")
    if top_neg[0] and top_neg[1] < -0.2:
        highlights.append(f"- {top_neg[0][:80]}")
    if not highlights:
        highlights.append("Mixed/neutral coverage")

    return score, highlights, {
        "articles_used": len(items),
        "top_headline": items[0].title if items else None,
    }
