from __future__ import annotations

from typing import Any

import pandas as pd

from .fibonacci import latest_fibonacci_levels
from .indicators import add_indicators
from .structure import describe_market_structure


def analyze_stock_frame(data: pd.DataFrame, pivot_window: int = 3) -> dict[str, Any]:
    """Build a descriptive technical snapshot; outputs are not trade instructions."""
    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if pivot_window < 1:
        raise ValueError("pivot_window must be at least 1")
    frame = data.dropna(subset=["Open", "High", "Low", "Close"]).copy()
    if frame.empty:
        raise ValueError("No usable OHLC rows")
    frame = add_indicators(frame)
    last = frame.iloc[-1]
    close = float(last["Close"])
    atr = float(last["ATR14"]) if pd.notna(last["ATR14"]) else None
    ema = {
        key: float(last[column]) if pd.notna(last[column]) else None
        for key, column in (("ema20", "EMA20"), ("ema50", "EMA50"), ("ema200", "EMA200"))
    }
    rsi = float(last["RSI14"]) if pd.notna(last["RSI14"]) else None
    macd = float(last["MACD"]) if pd.notna(last["MACD"]) else None
    macd_signal = float(last["MACDSignal"]) if pd.notna(last["MACDSignal"]) else None
    volume_avg = frame["Volume"].rolling(20, min_periods=20).mean().iloc[-1]
    volume_ratio = (
        float(last["Volume"] / volume_avg)
        if pd.notna(volume_avg) and volume_avg > 0 and pd.notna(last["Volume"])
        else None
    )

    structure = describe_market_structure(frame, pivot_window)
    fib = latest_fibonacci_levels(frame, pivot_window)

    bullish_checks = [
        ema["ema20"] is not None and close > ema["ema20"],
        ema["ema50"] is not None and close > ema["ema50"],
        ema["ema200"] is not None and close > ema["ema200"],
        rsi is not None and rsi >= 50,
        macd is not None and macd_signal is not None and macd > macd_signal,
        str(structure["trend"]).startswith("قمم وقيعان صاعدة"),
    ]
    bearish_checks = [
        ema["ema20"] is not None and close < ema["ema20"],
        ema["ema50"] is not None and close < ema["ema50"],
        ema["ema200"] is not None and close < ema["ema200"],
        rsi is not None and rsi <= 50,
        macd is not None and macd_signal is not None and macd < macd_signal,
        str(structure["trend"]).startswith("قمم وقيعان هابطة"),
    ]
    valid_checks = sum(
        value is not None
        for value in (
            ema["ema20"], ema["ema50"], ema["ema200"], rsi,
            macd, macd_signal
        )
    ) + (1 if structure["trend"] != "غير محدد" else 0)
    bullish_count = sum(bool(value) for value in bullish_checks)
    bearish_count = sum(bool(value) for value in bearish_checks)
    if valid_checks < 4:
        state = "بيانات غير كافية للحكم"
    elif bullish_count >= 4 and bullish_count - bearish_count >= 2:
        state = "ميل فني إيجابي متوافق نسبياً"
    elif bearish_count >= 4 and bearish_count - bullish_count >= 2:
        state = "ميل فني سلبي متوافق نسبياً"
    else:
        state = "قراءة مختلطة / انتقالية"

    scenarios = {
        "atr": atr,
        "reference_close": close,
        "upper_1atr": close + atr if atr is not None else None,
        "lower_1atr": close - atr if atr is not None else None,
        "upper_2atr": close + 2 * atr if atr is not None else None,
        "lower_2atr": close - 2 * atr if atr is not None else None,
        "note": "نطاقات حساسية حسابية مبنية على ATR وليست أهدافاً أو مستويات دخول/خروج.",
    }
    return {
        "frame": frame,
        "last_close": close,
        "as_of": str(frame.index[-1]),
        "bars": len(frame),
        "ema": ema,
        "rsi14": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "volume_ratio_20": volume_ratio,
        "structure": structure,
        "fibonacci": fib,
        "scenario_ranges": scenarios,
        "bullish_components": bullish_count,
        "bearish_components": bearish_count,
        "available_components": valid_checks,
        "descriptive_state": state,
        "method_note": (
            "النتيجة تلخيص وصفي لمكونات فنية محددة وليست احتمال نجاح أو توصية تداول. "
            "تتأثر بجودة البيانات والإطار الزمني وطريقة تأكيد المحاور."
        ),
    }
