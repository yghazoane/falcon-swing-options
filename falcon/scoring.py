from __future__ import annotations

import pandas as pd


def describe_confluence(frame: pd.DataFrame) -> str:
    """Return a plain-language description, not a probability or trade signal."""
    if len(frame) < 2:
        return "السجل التاريخي قصير لإجراء مقارنة وصفية."
    last = frame.iloc[-1]
    checks = []
    for column, label in (("EMA20", "EMA20"), ("EMA50", "EMA50"), ("EMA200", "EMA200")):
        value = last.get(column)
        if pd.notna(value):
            checks.append(f"السعر أعلى {label}" if last["Close"] > value else f"السعر أدنى {label}")
        else:
            checks.append(f"{label}: بيانات غير كافية")
    if pd.notna(last.get("RSI14")):
        checks.append(f"RSI={last['RSI14']:.1f}")
    if pd.notna(last.get("MACD")) and pd.notna(last.get("MACDSignal")):
        checks.append("MACD أعلى خط الإشارة" if last["MACD"] > last["MACDSignal"] else "MACD أدنى خط الإشارة")
    return "؛ ".join(checks) + ". هذه ملاحظات فنية تاريخية وليست توقعاً للمستقبل."
