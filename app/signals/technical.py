"""Technical indicators -> [-100, +100] per horizon."""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands


HORIZON_WEIGHTS = {
    "short":  {"rsi": 0.30, "macd": 0.25, "ma50": 0.20, "ma200": 0.05, "vol": 0.15, "bb": 0.05, "range52": 0.00},
    "medium": {"rsi": 0.15, "macd": 0.20, "ma50": 0.25, "ma200": 0.20, "vol": 0.10, "bb": 0.05, "range52": 0.05},
    "long":   {"rsi": 0.05, "macd": 0.10, "ma50": 0.15, "ma200": 0.40, "vol": 0.10, "bb": 0.05, "range52": 0.15},
}


def _clip(x: float) -> float:
    return max(-100.0, min(100.0, x))


def _rsi_score(df: pd.DataFrame) -> float:
    rsi = RSIIndicator(df["close"], window=14).rsi().iloc[-1]
    if np.isnan(rsi):
        return 0.0
    # 30 -> +100, 50 -> 0, 70 -> -100 (mean-reversion view)
    return _clip((50 - rsi) * 5)


def _macd_score(df: pd.DataFrame) -> float:
    macd = MACD(df["close"])
    line = macd.macd().iloc[-1]
    signal = macd.macd_signal().iloc[-1]
    hist = macd.macd_diff().iloc[-1]
    if np.isnan(hist):
        return 0.0
    base = 60 if line > signal else -60
    # Histogram magnitude scaled by recent close
    scale = (hist / df["close"].iloc[-1]) * 5000
    return _clip(base + np.sign(hist) * min(40, abs(scale)))


def _ma_score(df: pd.DataFrame, window: int) -> float:
    if len(df) < window:
        return 0.0
    ma = df["close"].rolling(window).mean().iloc[-1]
    price = df["close"].iloc[-1]
    if np.isnan(ma) or ma == 0:
        return 0.0
    pct = (price - ma) / ma * 100
    # +5% above -> +50, +10% -> +100
    return _clip(pct * 10)


def _golden_cross_bonus(df: pd.DataFrame) -> float:
    if len(df) < 210:
        return 0.0
    ma50 = df["close"].rolling(50).mean()
    ma200 = df["close"].rolling(200).mean()
    if np.isnan(ma50.iloc[-1]) or np.isnan(ma200.iloc[-1]):
        return 0.0
    diff = ma50.iloc[-1] - ma200.iloc[-1]
    return 20 if diff > 0 else -20


def _volume_score(df: pd.DataFrame) -> float:
    if len(df) < 25:
        return 0.0
    avg = df["volume"].tail(20).mean()
    today = df["volume"].iloc[-1]
    if avg == 0:
        return 0.0
    ratio = today / avg
    direction = 1 if df["close"].iloc[-1] > df["close"].iloc[-2] else -1
    if ratio > 1.5:
        return _clip(direction * 60)
    if ratio < 0.5:
        return _clip(-direction * 20)
    return _clip(direction * (ratio - 1) * 40)


def _bb_score(df: pd.DataFrame) -> float:
    bb = BollingerBands(df["close"], window=20, window_dev=2)
    upper = bb.bollinger_hband().iloc[-1]
    lower = bb.bollinger_lband().iloc[-1]
    price = df["close"].iloc[-1]
    if np.isnan(upper) or np.isnan(lower) or upper == lower:
        return 0.0
    pos = (price - lower) / (upper - lower)
    # 0 -> +80 (oversold), 1 -> -80 (overbought)
    return _clip((0.5 - pos) * 160)


def _range52_score(df: pd.DataFrame) -> float:
    window = df.tail(252) if len(df) >= 252 else df
    high = window["high"].max()
    low = window["low"].min()
    price = window["close"].iloc[-1]
    if high == low:
        return 0.0
    pos = (price - low) / (high - low)
    # Near 52w-high -> momentum positive but stretched; we treat upper third as +, lower third as -
    if pos > 0.85:
        return 60
    if pos > 0.6:
        return 30
    if pos < 0.15:
        return -40
    if pos < 0.35:
        return -10
    return 0


def score_technical(df: pd.DataFrame) -> Dict[str, Tuple[float, List[str], dict]]:
    """Return per-horizon (score, highlights, extras)."""
    components = {
        "rsi":   _rsi_score(df),
        "macd":  _macd_score(df),
        "ma50":  _ma_score(df, 50),
        "ma200": _clip(_ma_score(df, 200) + _golden_cross_bonus(df)),
        "vol":   _volume_score(df),
        "bb":    _bb_score(df),
        "range52": _range52_score(df),
    }

    # Highlights derived from the strongest components.
    highlights: List[str] = []
    price = df["close"].iloc[-1]
    ma50 = df["close"].rolling(50).mean().iloc[-1] if len(df) >= 50 else float("nan")
    ma200 = df["close"].rolling(200).mean().iloc[-1] if len(df) >= 200 else float("nan")
    if not np.isnan(ma200):
        highlights.append("Price > 200DMA" if price > ma200 else "Price < 200DMA")
    if not np.isnan(ma50) and not np.isnan(ma200):
        if ma50 > ma200:
            highlights.append("Golden cross (50>200)")
        else:
            highlights.append("Death cross (50<200)")
    rsi_val = RSIIndicator(df["close"], window=14).rsi().iloc[-1]
    if not np.isnan(rsi_val):
        highlights.append(f"RSI {rsi_val:.0f}")

    out: Dict[str, Tuple[float, List[str], dict]] = {}
    for horizon, weights in HORIZON_WEIGHTS.items():
        score = sum(weights[k] * components[k] for k in weights)
        out[horizon] = (_clip(score), highlights, {"components": components})
    return out
