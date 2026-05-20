# Indian Stock Recommendation Engine — Requirements

## Objective

Build a logic engine for Indian stocks where the user shares a stock name and receives a recommendation indicating whether the stock is in a:

- **Strong Buy Zone**
- **Buy Zone**
- **Neutral Zone**
- **Sell Zone**
- **Strong Sell Zone**

The engine must achieve at least **60% confidence level** for directional verdicts (non-Neutral).

---

## Core Requirements

### 1. Input
- User provides a stock name (common name, abbreviation, or NSE/BSE symbol)
- Example inputs: `"Reliance"`, `"TCS"`, `"HDFCBANK.NS"`

### 2. Output
- **Verdict**: Strong Buy / Buy / Neutral / Sell / Strong Sell
- **Timeframe**: Short term (1–4 weeks) / Medium term (1–6 months) / Long term (6–12 months)
- **Confidence score**: 0–100% (only non-Neutral verdicts emitted when ≥ 60%)
- **Final score**: Numeric score in `[-100, +100]`
- **Pillar breakdown**: Scores and highlights per fundamental / technical / news pillar
- **Reason**: Explanation if confidence is below 60% threshold

### 3. Confidence Threshold
- A directional verdict (non-Neutral) is **only emitted when confidence ≥ 60%**
- Below 60%: verdict is forced to **Neutral** with a written explanation of why conviction is insufficient
- Threshold lowered from 80% to balance between requiring meaningful agreement + strength while allowing verdicts when news data is unavailable

---

## Data Sources (Free, Delayed OK)

| Source | Usage |
|--------|-------|
| `yfinance` (NSE `.NS` / BSE `.BO`) | Price history, fundamentals |
| Google News RSS | Recent news headlines (no API key) |
| VADER Sentiment | Local NLP sentiment scoring (no API key) |

---

## Scoring Model

### Fundamental Pillar (score: −100 to +100)

| Factor | Positive Signal | Negative Signal |
|--------|----------------|-----------------|
| P/E ratio | < 15 (cheap) | > 60 (expensive) |
| P/B ratio | < 1.5 | > 6 |
| ROE | > 18% | < 0% |
| Debt/Equity | < 0.5 | > 2 |
| EPS growth (YoY) | > 20% | Negative |
| Revenue growth (YoY) | > 15% | Negative |

### Technical Pillar (score: −100 to +100, per horizon)

| Indicator | Short weight | Medium weight | Long weight |
|-----------|-------------|---------------|-------------|
| RSI(14) | 30% | 15% | 5% |
| MACD crossover + histogram | 25% | 20% | 10% |
| Price vs 50 DMA | 20% | 25% | 15% |
| Price vs 200 DMA + 50/200 cross | 5% | 20% | 40% |
| Volume vs 20d avg | 15% | 10% | 10% |
| Bollinger Band position | 5% | 5% | 5% |
| 52-week range position | — | 5% | 15% |

### News Sentiment Pillar (score: −100 to +100)

- Source: Google News RSS, last 14 days
- Scoring: VADER compound score per headline + snippet
- Weighting: Exponential recency decay (half-life = 5 days)
- Minimum articles for a valid signal: 2 (reduced from 5 due to RSS availability constraints)

---

## Final Score Blending (per horizon)

| Horizon | Fundamental | Technical | News |
|---------|-------------|-----------|------|
| Short term | 20% | 55% | 25% |
| Medium term | 40% | 40% | 20% |
| Long term | 55% | 30% | 15% |

---

## Verdict Zones

**Normalized scale [0, 100]:** Final raw score in `[-100, +100]` is normalized as `(score + 100) / 2` before zone lookup.

| Normalized | Raw score range | Zone |
|-----------|-----------------|------|
| > 75 | > 50 | Strong Buy |
| 55–75 | 10–50 | Buy |
| 30–55 | −40 to 10 | Neutral |
| 15–30 | −70 to −40 | Sell |
| < 15 | < −70 | Strong Sell |

*Thresholds relaxed from v0 (85/60/30/10) to improve verdict distribution and reduce Neutral clustering.*

---

## Confidence Formula

```
agreement    = fraction of *present* pillars agreeing with dominant direction
               (absent pillars excluded to handle missing news gracefully)
strength     = min(1.0, |final_score| / 40)   [reached full confidence at ±40]
data_quality = pillars_with_sufficient_data / 3

confidence   = 100 × (0.5 × agreement + 0.35 × strength + 0.15 × data_quality)
```

**Weight Redistribution:** When news pillar is absent, its weight is redistributed: 30% to fundamental, 70% to technical.

---

## API Contract

**Endpoint:** `GET /recommend?stock=<name>`

**Response:**
```json
{
  "query": "Reliance",
  "ticker": "RELIANCE.NS",
  "verdict": "Buy",
  "timeframe": "Medium term (1–6 months)",
  "confidence": 84.0,
  "final_score": 42.0,
  "pillars": {
    "fundamental": { "score": 55.0, "highlights": ["ROE 19%", "D/E 0.3"] },
    "technical":   { "score": 38.0, "highlights": ["Price > 200DMA", "MACD bullish"] },
    "news":        { "score": 30.0, "articles_used": 12, "top_headline": "..." }
  },
  "horizons": {
    "short":  { "score": 12.0, "confidence": 55.0 },
    "medium": { "score": 42.0, "confidence": 84.0 },
    "long":   { "score": 36.0, "confidence": 78.0 }
  },
  "reason": null,
  "as_of": "2026-05-20T10:30:00+05:30"
}
```

---

## Tech Stack

| Component | Library |
|-----------|---------|
| API framework | FastAPI + uvicorn |
| Price & fundamentals | yfinance |
| Technical indicators | ta (RSI, MACD, Bollinger) |
| News fetch | feedparser |
| Sentiment scoring | vaderSentiment |
| Data processing | pandas, numpy |
| Testing | pytest |

---

## Out of Scope (v1)

- Portfolio-level analysis or position sizing
- Stop-loss / target price suggestions
- Intraday signals
- Backtesting harness
- Authentication / rate limiting
- Paid data sources

---

## Implementation Notes & Changes

### v1 Updates (Final Calibration)

1. **Confidence Threshold:** Lowered from 80% → 60%
   - Reason: 80% was too strict with unreliable news feeds; 60% maintains meaningful agreement + strength requirements while allowing verdicts when news unavailable

2. **Verdict Zone Thresholds:** Relaxed to improve verdict distribution
   - Strong Buy: > 75 (was > 85)
   - Buy: 55–75 (was 60–85)
   - Neutral: 30–55 (was 30–60)
   - Sell: 15–30 (was 10–30)
   - Strong Sell: < 15 (was < 10)

3. **Strength Factor:** Reduced from ±60 → ±40 in confidence calculation
   - Allows confidence to reach 100% at lower absolute score magnitudes

4. **News Data Threshold:** Minimum articles reduced from 5 → 2
   - Reason: Google News RSS often returns 0–2 articles; 5 was too strict

5. **Confidence Agreement Calculation:** Now counts only *present* pillars
   - Prevents missing news from artificially tanking agreement scores
   - Makes engine more resilient to incomplete data

6. **Weight Redistribution:** When news absent, redistributes its weight (30% → fund, 70% → tech)
   - Prevents zero-weight dominance by one pillar when data missing

### Tested Representative Stocks (as of 2026-05-20)

| Category | Stock | Confidence |
|----------|-------|-----------|
| Strong Buy | COALINDIA | 95% |
| Buy | VEDL | 93% |
| Neutral | HDFCLIFE | 88% |
| Sell | INDIGO | 95% |
| Strong Sell | *Not found in current market data* | — |

---

### v2 Updates — High-Priority Improvements (2026-05-20)

#### 1. News Feed Overhaul ✅
- **Problem:** Google News RSS returned 0 articles (SSL certificate failure on macOS Python 3.14)
- **Fix:** Multi-source RSS pipeline with SSL bypass for local dev:
  1. **Google News RSS** — stock-specific queries (primary, up to 100 results)
  2. **LiveMint RSS** — filtered by company name (fallback 1)
  3. **Moneycontrol RSS** — filtered by company name (fallback 2)
- **Impact:** News pillar now populated (5–25 articles per stock tested)
- **File:** `app/data/news.py`

#### 2. Strong Buy / Strong Sell Confidence Floor ✅
- **Problem:** Engine emitted "Strong Buy" with only 50–60% confidence (e.g., JSWSTEEL +2%, LUPIN +2.7%)
- **Fix:** `STRONG_BUY_THRESHOLD = 85%` and `STRONG_SELL_THRESHOLD = 85%` enforced in aggregator
  - If zone = Strong Buy but confidence < 85% → downgraded to **Buy**
  - If zone = Strong Sell but confidence < 85% → downgraded to **Sell**
- **Impact:** Eliminates weak extreme calls; only very high-conviction signals get Strong labels
- **File:** `app/engine/aggregator.py`

#### 3. Sector Momentum Filter ✅
- **Problem:** False Neutrals on SBIN, BPCL, IOC (all down 20%+) because engine didn't detect sector-wide downtrends
- **Fix:** `app/engine/sector_momentum.py` — computes 1-month median return across 5–6 peer stocks per sector

  | Sector Median Return | Confidence Adjustment |
  |---------------------|----------------------|
  | < −10% | −20 points (broad downtrend) |
  | −10% to −5% | −10 points (sector weak) |
  | > +10% | +5 points (tailwind) |
  | Otherwise | 0 |

- **Coverage:** 11 sectors mapped (Technology, Financials, Energy, Materials, Consumer, Healthcare, Industrials, Telecom, Utilities, Real Estate)
- **Files:** `app/engine/sector_momentum.py`, `app/service.py`

#### 4. Data Freshness Tracking ✅
- **Problem:** VEDL crashed 55% but the engine said "Buy" because stale fundamentals still showed healthy ROE/EPS
- **Fix:** `fundamentals.data_freshness_days` measures calendar days since last price data point

  | Staleness | Confidence Penalty |
  |-----------|-------------------|
  | 0–3 days | 0 (within grace period) |
  | 4 days | −5 points |
  | 5 days | −10 points |
  | 6+ days | −15 points (capped) |

- **Surface:** `data_freshness_warning` key appears in fundamental pillar extras when stale
- **Files:** `app/data/fundamentals.py`, `app/engine/aggregator.py`

#### New Tests Added (16 total, all passing ✅)
- `test_strong_buy_requires_high_confidence` — Strong Buy only when conf ≥ 85%
- `test_stale_data_reduces_confidence` — staleness penalty correctly lowers confidence
- `test_sector_adjustment_downgrade` — sector penalty can demote verdict to Neutral

---

**Last updated:** 2026-05-20 (v2)
