from __future__ import annotations

from datetime import time
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from .indicators import add_indicators
from .market import load_history
from .structure import describe_market_structure

NEW_YORK = ZoneInfo("America/New_York")


def _ordered(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    if isinstance(frame.index, pd.DatetimeIndex):
        frame = frame[~frame.index.isna()]
        frame = frame[~frame.index.duplicated(keep="last")].sort_index(kind="stable")
    return frame


def _regular_session_four_hour_bars(hourly: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly bars into NYSE-session anchored 4H buckets.

    The final bucket of a regular session is naturally shorter than four hours.
    This is a derived view, not an exchange-native four-hour candle.
    """
    if hourly.empty:
        return pd.DataFrame()
    frame = _ordered(hourly)
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("Hourly history must have a DatetimeIndex")
    if frame.index.tz is None:
        frame.index = frame.index.tz_localize(NEW_YORK)
    else:
        frame.index = frame.index.tz_convert(NEW_YORK)

    session_mask = [
        time(9, 30) <= timestamp.time() < time(16, 0)
        for timestamp in frame.index
    ]
    frame = frame.loc[session_mask]
    if frame.empty:
        return pd.DataFrame()

    chunks = []
    session_dates = pd.Index(frame.index.date).unique()
    for session_date in session_dates:
        session = frame.loc[[stamp.date() == session_date for stamp in frame.index]]
        if session.empty:
            continue
        aggregated = session.resample(
            "4h", origin="start_day", offset="9h30min",
            label="left", closed="left",
        ).agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum",
        })
        counts = session["Close"].resample(
            "4h", origin="start_day", offset="9h30min",
            label="left", closed="left",
        ).count()
        aggregated["source_hour_bars"] = counts
        aggregated = aggregated.dropna(subset=["Open", "High", "Low", "Close"])
        chunks.append(aggregated)
    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks).sort_index()


def analyze_timeframe(data: pd.DataFrame, timeframe: str, source: str) -> dict[str, Any]:
    """Create a descriptive multi-indicator snapshot for one timeframe."""
    frame = _ordered(data)
    result: dict[str, Any] = {
        "timeframe": timeframe, "trend": "بيانات غير كافية", "momentum": "غير واضح",
        "volume_state": "غير متاح", "structure": "غير محدد", "structure_event": "غير متاح",
        "close": None, "ema20": None, "ema50": None, "ema200": None, "rsi14": None,
        "macd_state": "غير متاح", "volume_ratio": None, "bars": int(len(frame)),
        "source": source, "status": "insufficient",
    }
    if frame.empty or "Close" not in frame:
        return result
    frame = add_indicators(frame)
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
            result["volume_state"] = (
                "أعلى من متوسط 20 شمعة" if ratio > 1.2
                else "أقل من متوسط 20 شمعة" if ratio < 0.8
                else "قريب من المتوسط"
            )
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
    """Load daily/hourly history and derive NYSE-session anchored 4H bars."""
    rows: list[dict[str, Any]] = []
    try:
        daily = load_history(symbol, period="1y", interval="1d")
        rows.append(analyze_timeframe(daily, "1D", "شموع يومية معدّلة من المزود"))
    except Exception as exc:
        rows.append(analyze_timeframe(pd.DataFrame(), "1D", f"تعذر التحميل: {type(exc).__name__}"))
    try:
        hourly = load_history(symbol, period="60d", interval="1h")
        rows.append(analyze_timeframe(hourly, "1H", "شموع ساعة من المزود؛ قد تكون متأخرة"))
        if not hourly.empty:
            four_hour = _regular_session_four_hour_bars(hourly)
            rows.append(analyze_timeframe(
                four_hour, "4H مشتق",
                "تجميع جلسة نيويورك من 09:30؛ الشمعة الأخيرة أقصر وقد تكون البيانات ناقصة",
            ))
        else:
            rows.append(analyze_timeframe(pd.DataFrame(), "4H مشتق", "لا تتوفر شموع ساعة للاشتقاق"))
    except Exception as exc:
        rows.append(analyze_timeframe(pd.DataFrame(), "1H", f"تعذر التحميل: {type(exc).__name__}"))
        rows.append(analyze_timeframe(pd.DataFrame(), "4H مشتق", f"تعذر التجميع: {type(exc).__name__}"))
    return rows, summarize_alignment(rows)
