from __future__ import annotations

from typing import Any

import pandas as pd

from .fibonacci import latest_fibonacci_levels
from .indicators import add_indicators
from .structure import describe_market_structure
from .volume_profile import volume_by_price


def analyze_stock_technicals(data: pd.DataFrame, pivot_window: int = 3) -> dict[str, Any]:
    """Build an explainable descriptive stock-analysis snapshot from historical OHLCV."""
    if pivot_window < 1:
        raise ValueError("pivot_window must be at least 1")
    if data.empty:
        return {
            "status": "unavailable", "note": "لا توجد بيانات سعرية كافية للتحليل.",
            "trend": "غير متاح", "momentum": "غير متاح", "volume": "غير متاح",
            "structure": {}, "fibonacci": {"levels": {}, "extensions": {}},
            "support": None, "resistance": None, "atr": None, "atr_pct": None,
            "atr_scenarios": {}, "volume_profile_poc": None,
        }

    frame = data.copy()
    required = {"EMA20", "EMA50", "EMA200", "RSI14", "MACD", "MACDSignal", "ATR14", "VWAP"}
    if not required.issubset(frame.columns):
        frame = add_indicators(frame)
    last = frame.iloc[-1]
    close = float(last["Close"])

    values: dict[str, float | None] = {}
    for col in ("EMA20", "EMA50", "EMA200", "RSI14", "MACD", "MACDSignal", "ATR14", "VWAP"):
        value = last.get(col)
        values[col.lower()] = float(value) if pd.notna(value) else None

    e20, e50, e200 = values["ema20"], values["ema50"], values["ema200"]
    if e20 is None or e50 is None:
        trend = "بيانات غير كافية"
    elif close > e20 > e50 and (e200 is None or e50 > e200):
        trend = "ترتيب متوسطات صاعد"
    elif close < e20 < e50 and (e200 is None or e50 < e200):
        trend = "ترتيب متوسطات هابط"
    else:
        trend = "متداخل / انتقالي"

    rsi = values["rsi14"]
    if rsi is None:
        momentum = "بيانات زخم غير كافية"
    elif rsi >= 70:
        momentum = "زخم مرتفع — منطقة تشبع محتملة"
    elif rsi >= 55:
        momentum = "زخم إيجابي"
    elif rsi <= 30:
        momentum = "زخم منخفض — منطقة تشبع محتملة"
    elif rsi <= 45:
        momentum = "زخم سلبي"
    else:
        momentum = "زخم محايد"

    macd_state = "غير متاح"
    if values["macd"] is not None and values["macdsignal"] is not None:
        macd_state = "MACD أعلى خط الإشارة" if values["macd"] > values["macdsignal"] else "MACD أدنى خط الإشارة"

    atr = values["atr14"]
    atr_pct = (atr / close * 100) if atr is not None and close else None
    atr_scenarios = {}
    if atr is not None:
        atr_scenarios = {
            "minus_1_atr": close - atr, "plus_1_atr": close + atr,
            "minus_2_atr": close - 2 * atr, "plus_2_atr": close + 2 * atr,
        }

    volume_ratio = None
    volume_state = "غير متاح"
    if "Volume" in frame and len(frame) >= 21:
        avg_volume = frame["Volume"].rolling(20, min_periods=20).mean().iloc[-1]
        if pd.notna(avg_volume) and float(avg_volume) > 0:
            volume_ratio = float(last["Volume"] / avg_volume)
            volume_state = (
                "أعلى بوضوح من متوسط 20 شمعة" if volume_ratio >= 1.5
                else "أعلى من متوسط 20 شمعة" if volume_ratio >= 1.2
                else "أقل من متوسط 20 شمعة" if volume_ratio < 0.8
                else "قريب من متوسط 20 شمعة"
            )

    structure = describe_market_structure(frame, pivot_window)
    support = structure.get("last_pivot_low")
    resistance = structure.get("last_pivot_high")
    fib = latest_fibonacci_levels(frame, pivot_window)
    profile = volume_by_price(frame)
    poc = None
    if not profile.empty and float(profile["volume"].sum()) > 0:
        poc_row = profile.loc[profile["volume"].idxmax()]
        poc = float(poc_row["price_level"])

    return {
        "status": "available",
        "close": close,
        "as_of": str(frame.index[-1]),
        "bars": int(len(frame)),
        "trend": trend,
        "momentum": momentum,
        "macd_state": macd_state,
        "volume": volume_state,
        "volume_ratio": volume_ratio,
        "structure": {
            "trend": structure["trend"], "event": structure["event"],
            "event_type": structure["event_type"],
            "last_pivot_low": support, "last_pivot_high": resistance,
            "note": structure["note"],
        },
        "support": support,
        "resistance": resistance,
        "fibonacci": fib,
        "volume_profile_poc": poc,
        "atr": atr,
        "atr_pct": atr_pct,
        "atr_scenarios": atr_scenarios,
        "indicators": values,
        "note": (
            "تحليل وصفي مبني على الشموع التاريخية المتاحة. مستويات المحاور مؤكدة بعد اكتمال شموعها اللاحقة؛ "
            "Volume Profile تقريبي من بيانات الشموع؛ ونطاقات ATR سيناريوهات قياس تقلب وليست أهدافاً أو أوامر."
        ),
    }
