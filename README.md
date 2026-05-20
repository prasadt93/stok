# Indian Stock Recommendation Engine

Free, multi-factor recommendation engine for Indian (NSE/BSE) stocks. Blends **fundamentals + technicals + news sentiment** into a verdict (Strong Buy / Buy / Neutral / Sell / Strong Sell) with a **timeframe** and an explicit **confidence score**. Only emits a directional call when confidence ≥ 80%; otherwise returns Neutral with a reason.

## Quick start

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Run the API
uvicorn app.main:app --reload
# then:
curl 'http://localhost:8000/recommend?stock=Reliance'

# Run tests
PYTHONPATH=. pytest tests/ -v
```

## How the score works

| Pillar       | Inputs                                                                 |
|--------------|------------------------------------------------------------------------|
| Fundamental  | P/E, P/B, ROE, Debt/Equity, EPS growth, Revenue growth (yfinance)      |
| Technical    | RSI, MACD, 50DMA, 200DMA + golden cross, Volume, Bollinger, 52w range  |
| News         | VADER sentiment over last 14d of Google News RSS, recency-decayed      |

Each pillar emits a score in `[-100, +100]`. Per-horizon blend:

| Horizon | Fundamental | Technical | News |
|---------|-------------|-----------|------|
| Short   | 20%         | 55%       | 25%  |
| Medium  | 40%         | 40%       | 20%  |
| Long    | 55%         | 30%       | 15%  |

Confidence = `0.5·agreement + 0.35·strength + 0.15·data_quality` (×100). The engine picks the horizon with confidence ≥ 80% and the largest |score|, preferring longer horizons on ties.

## Files

- `app/main.py` — FastAPI app, `/recommend` endpoint
- `app/service.py` — Orchestrator (data → signals → aggregate)
- `app/resolver.py` — Name → NSE/BSE ticker (`Reliance` → `RELIANCE.NS`)
- `app/data/` — yfinance prices/fundamentals, Google News RSS
- `app/signals/` — Per-pillar scorers
- `app/engine/aggregator.py` — Weighted blend + confidence + horizon picker
- `app/engine/zones.py` — Score → verdict label

## Calibration

Weights and zone thresholds are constants in `app/engine/aggregator.py` and `app/signals/technical.py`. Run the engine on 15–20 well-known names and tune until verdicts match common knowledge and confidence ≥ 80% triggers reasonably often.
