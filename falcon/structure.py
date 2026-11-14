from __future__ import annotations
import pandas as pd

def add_confirmed_pivots(data: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    """Mark swing pivots only after the required right-side bars have completed."""
    if window < 1:
        raise ValueError("window must be at least 1")
    df = data.copy()
    span = 2 * window + 1
    high_max = df["High"].rolling(span, center=True, min_periods=span).max()
    low_min = df["Low"].rolling(span, center=True, min_periods=span).min()
    df["PivotHigh"] = df["High"].where(df["High"].eq(high_max))
    df["PivotLow"] = df["Low"].where(df["Low"].eq(low_min))
    return df

def describe_market_structure(data: pd.DataFrame, window: int = 3) -> dict[str, object]:
    df = add_confirmed_pivots(data, window)
    highs, lows = df["PivotHigh"].dropna(), df["PivotLow"].dropna()
    last_close = float(df["Close"].iloc[-1]) if len(df) else float("nan")
    last_high = float(highs.iloc[-1]) if not highs.empty else None
    last_low = float(lows.iloc[-1]) if not lows.empty else None
    if last_high is not None and last_close > last_high:
        event = "إغلاق أعلى آخر قمة محورية مؤكدة"
    elif last_low is not None and last_close < last_low:
        event = "إغلاق أدنى آخر قاع محوري مؤكد"
    else:
        event = "لا يوجد تجاوز للإغلاق للمستويات المحورية الأخيرة"
    trend = "غير محدد"
    if len(highs) >= 2 and len(lows) >= 2:
        if highs.iloc[-1] > highs.iloc[-2] and lows.iloc[-1] > lows.iloc[-2]:
            trend = "قمم وقيعان صاعدة"
        elif highs.iloc[-1] < highs.iloc[-2] and lows.iloc[-1] < lows.iloc[-2]:
            trend = "قمم وقيعان هابطة"
        else:
            trend = "هيكل متداخل/عرضي"
    return {"trend": trend, "event": event, "last_pivot_high": last_high,
            "last_pivot_low": last_low, "annotated": df,
            "note": "لا يتأكد المحور إلا بعد اكتمال الشموع اللاحقة المحددة؛ وقد تتأخر قراءته."}
