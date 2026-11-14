from __future__ import annotations
import pandas as pd
from .structure import add_confirmed_pivots

def latest_fibonacci_levels(data: pd.DataFrame, window: int = 3) -> dict[str, object]:
    df = add_confirmed_pivots(data, window)
    pivots = []
    for idx, row in df.iterrows():
        if pd.notna(row["PivotHigh"]):
            pivots.append((idx, "high", float(row["PivotHigh"])))
        if pd.notna(row["PivotLow"]):
            pivots.append((idx, "low", float(row["PivotLow"])))
    pivots.sort(key=lambda item: item[0])
    pair = None
    for first, second in zip(pivots, pivots[1:]):
        if first[1] != second[1]:
            pair = (first, second)
    if pair is None:
        return {"levels": {}, "direction": "غير متاح", "note": "لا توجد نقاط محورية متعاكسة مؤكدة كفاية."}
    first, second = pair
    low, high = sorted((first[2], second[2]))
    if high == low:
        return {"levels": {}, "direction": "غير متاح", "note": "نطاق الحركة يساوي صفراً."}
    direction = "صعود" if first[1] == "low" and second[1] == "high" else "هبوط"
    ratios = (0.236, 0.382, 0.5, 0.618, 0.786)
    if direction == "صعود":
        levels = {f"{r:.3f}": high - (high - low) * r for r in ratios}
    else:
        levels = {f"{r:.3f}": low + (high - low) * r for r in ratios}
    return {"levels": levels, "direction": direction, "swing_low": low,
            "swing_high": high,
            "note": "مستويات حسابية من آخر ساق محورية مؤكدة، وليست دعماً أو مقاومة مضمونة."}
