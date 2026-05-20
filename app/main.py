"""FastAPI entrypoint — serves UI at / and API at /recommend."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse

from app.schemas import RecommendationResponse
from app.service import recommend

app = FastAPI(title="Indian Stock Recommendation Engine", version="0.1.0")

_HTML_PATH = Path(__file__).parent.parent / "index.html"


@app.get("/", response_class=HTMLResponse)
def ui():
    return _HTML_PATH.read_text()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/recommend", response_model=RecommendationResponse)
def get_recommendation(stock: str = Query(..., min_length=1, description="Stock name or NSE/BSE symbol")):
    try:
        return recommend(stock)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Engine error: {e}")


NIFTY_100 = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC",
    "LT", "AXISBANK", "KOTAKBANK", "HINDUNILVR", "BAJFINANCE", "MARUTI", "SUNPHARMA",
    "WIPRO", "ULTRACEMCO", "ASIANPAINT", "TITAN", "NESTLEIND", "BAJAJFINSV", "TECHM",
    "HCLTECH", "POWERGRID", "NTPC", "JSWSTEEL", "TATASTEEL", "HINDALCO", "COALINDIA",
    "ONGC", "BPCL", "GRASIM", "DIVISLAB", "DRREDDY", "CIPLA", "EICHERMOT", "HEROMOTOCO",
    "BAJAJ-AUTO", "M&M", "TATACONSUM", "BRITANNIA", "PIDILITIND", "SIEMENS", "HAVELLS",
    "DABUR", "MARICO", "COLPAL", "GODREJCP", "BERGEPAINT", "AMBUJACEM", "SHREECEM",
    "ADANIPORTS", "ADANIGREEN", "ADANIENT", "INDUSINDBK", "FEDERALBNK", "BANKBARODA",
    "CANBK", "PNB", "IDFCFIRSTB", "CHOLAFIN", "MUTHOOTFIN", "LICHSGFIN", "SBICARD",
    "LTIM", "COFORGE", "PERSISTENT", "MPHASIS", "OFSS", "CONCOR", "DELHIVERY",
    "APOLLOTYRE", "MRF", "BOSCH", "EXIDEIND", "BHEL", "GAIL", "TATAPOWER",
    "JSWENERGY", "TORNTPOWER", "TORNTPHARM", "LUPIN", "AUROPHARMA", "GLENMARK",
    "IPCALAB", "ALKEM", "LALPATHLAB", "METROPOLIS", "APOLLOHOSP", "MAXHEALTH",
    "ZOMATO", "NYKAA", "PAYTM", "DMART", "TRENT", "PAGEIND", "MCDOWELL-N",
    "UNITDSPR", "RADICO", "JINDALSTEL",
]


@app.get("/nifty100/stream")
def stream_nifty100():
    """Stream per-stock results via Server-Sent Events."""
    total = len(NIFTY_100)

    def generate():
        results: dict[str, list] = {}
        errors = []

        for idx, ticker in enumerate(NIFTY_100, start=1):
            try:
                rec = recommend(ticker)
                entry = {
                    "ticker": rec.ticker,
                    "verdict": rec.verdict,
                    "confidence": rec.confidence,
                    "final_score": rec.final_score,
                    "timeframe": rec.timeframe,
                    "short_term": rec.horizons["short"].verdict,
                    "medium_term": rec.horizons["medium"].verdict,
                    "long_term": rec.horizons["long"].verdict,
                }
                results.setdefault(rec.verdict, []).append(entry)
                payload = json.dumps({"type": "progress", "done": idx, "total": total, "stock": entry})
            except Exception as e:
                errors.append({"ticker": ticker, "error": str(e)})
                payload = json.dumps({"type": "progress", "done": idx, "total": total, "stock": None, "ticker": ticker, "error": str(e)})

            yield f"data: {payload}\n\n"

        final = json.dumps({
            "type": "done",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_analyzed": total - len(errors),
            "results": results,
            "errors": errors,
        })
        yield f"data: {final}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
