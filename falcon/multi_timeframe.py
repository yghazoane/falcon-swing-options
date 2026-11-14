from __future__ import annotations

from typing import Any

import pandas as pd

from .indicators import add_indicators
from .market import load_history
from .structure import describe_market_structure


def analyze_timeframe(data: pd.DataFrame, timeframe: str, source: str) -> dict[str, Any]:
    """Create a descriptive multi-indicator snapshot for one timeframe."""
    result: dict[str, Any] = {
        "timeframe": timeframe, "trend": "بيانات غير كافية", "momentum": "غير واضح",
        "volume_state": "غير متاح", "structure": "غير محدد", "structure_event": "غير متاح",
        "close": None, "ema20": None, "ema50": None, "ema200": None, "rsi14": None,
        "macd_state": "غير متاح", "volume_ratio": None, "bars": int(len(data)),
        "source": source, "status": "insufficient",
    }
    if data.empty or "Close" not in data:
        return result
    frame = add_indicators(data)
    last = frame.iloc[-1]
    result["close"] = float(last["Close"])
    for column, key in (("EMA20", "ema20"), ("EMA50", "ema50"), ("EMA200", "ema200")):
        value = last.get(column)
        result[key] = float(value) if pd.notna(value) else None
    e20, e50, e200 = result["ema20"], result["ema50"], result["ema200"]
    if e20 is not None and e50 is not None:
        if e200 is not None and result["close"] > e20 > e50 > e200:
            result["trend"] = "صاعد متوافق"
        elif e200 is not None and result["close"] < e20 < e50 < e200:
            result["trend"] = "هابط متوافق"
        elif result["close"] > e20 > e50:
            result["trend"] = "صاعد متوسط"
        elif result["close"] < e20 < e50:
            result["trend"] = "هابط متوسط"
        else:
            result["trend"] = "مختلط / انتقالي"
        result["status"] = "available"
    rsi = last.get("RSI14")
    if pd.notna(rsi):
        result["rsi14"] = float(rsi)
        result["momentum"] = "زخم إيجابي" if rsi >= 55 else "زخم سلبي" if rsi <= 45 else "زخم محايد"
    macd, signal = last.get("MACD"), last.get("MACDSignal")
    if pd.notna(macd) and pd.notna(signal):
        result["macd_state"] = "MACD أعلى الإشارة" if macd > signal else "MACD أدنى الإشارة"
    if "Volume" in frame and len(frame) >= 21:
        average = frame["Volume"].rolling(20, min_periods=20).mean().iloc[-1]
        if pd.notna(average) and average > 0:
            ratio = float(last["Volume"] / average)
            result["volume_ratio"] = ratio
            result["volume_state"] = "أعلى من متوسط 20 شمعة" if ratio > 1.2 else "أقل من متوسط 20 شمعة" if ratio < 0.8 else "قريب من المتوسط"
    structure = describe_market_structure(frame)
    result["structure"] = str(structure["trend"])
    result["structure_event"] = str(structure["event"])
    return result


def summarize_alignment(rows: list[dict[str, Any]]) -> dict[str, str | int]:
    """Summarize timeframe agreement without turning it into a forecast."""
    usable = [row for row in rows if row.get("status") == "available"]
    bullish = sum(str(row["trend"]).startswith("صاعد") for row in usable)
    bearish = sum(str(row["trend"]).startswith("هابط") for row in usable)
    mixed = len(usable) - bullish - bearish
    if not usable:
        label = "لا توجد بيانات كافية للمقارنة"
    elif bullish == len(usable):
        label = "اتساق صاعد بين الأطر المتاحة"
    elif bearish == len(usable):
        label = "اتساق هابط بين الأطر المتاحة"
    elif bullish and bearish:
        label = "تعارض بين الأطر الزمنية"
    else:
        label = "اتجاه مختلط أو انتقالي"
    return {
        "label": label, "available_timeframes": len(usable),
        "bullish_timeframes": bullish, "bearish_timeframes": bearish,
        "mixed_timeframes": mixed,
        "note": "وصف لاتفاق المؤشرات التاريخية فقط؛ لا يمثل احتمال نجاح أو إشارة تداول.",
    }


def load_multi_timeframe(symbol: str) -> tuple[list[dict[str, Any]], dict[str, str | int]]:
    """Load daily/hourly history and derive 4H bars from hourly data."""
    rows: list[dict[str, Any]] = []
    try:
        daily = load_history(symbol, period="1y", interval="1d")
        rows.append(analyze_timeframe(daily, "1D", "شموع يومية من المزود"))
    except Exception:
        rows.append(analyze_timeframe(pd.DataFrame(), "1D", "غير متاح"))
    try:
        hourly = load_history(symbol, period="60d", interval="1h")
        rows.append(analyze_timeframe(hourly, "1H", "شموع ساعة من المزود"))
        if not hourly.empty:
            four_hour = hourly.resample("4h").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum",
            }).dropna(subset=["Open", "High", "Low", "Close"])
            rows.append(analyze_timeframe(four_hour, "4H مشتق", "تجميع شموع الساعة؛ ليس إطاراً أصلياً من المزود"))
        else:
            rows.append(analyze_timeframe(pd.DataFrame(), "4H مشتق", "لا تتوفر شموع ساعة للاشتقاق"))
    except Exception:
        rows.append(analyze_timeframe(pd.DataFrame(), "1H", "غير متاح"))
        rows.append(analyze_timeframe(pd.DataFrame(), "4H مشتق", "غير متاح"))
    return rows, summarize_alignment(rows)
