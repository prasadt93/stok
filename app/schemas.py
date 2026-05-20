from typing import Literal, Optional
from pydantic import BaseModel

Verdict = Literal["Strong Buy", "Buy", "Neutral", "Sell", "Strong Sell"]
Horizon = Literal["short", "medium", "long"]

HORIZON_LABEL = {
    "short": "Short term (1–4 weeks)",
    "medium": "Medium term (1–6 months)",
    "long": "Long term (6–12 months)",
}


class PillarBreakdown(BaseModel):
    score: float
    highlights: list[str] = []
    extras: dict = {}


class HorizonScore(BaseModel):
    score: float
    confidence: float
    verdict: str


class RecommendationResponse(BaseModel):
    query: str
    ticker: str
    verdict: Verdict
    timeframe: str
    confidence: float
    final_score: float
    pillars: dict[str, PillarBreakdown]
    horizons: dict[str, HorizonScore]
    reason: Optional[str] = None
    as_of: str
