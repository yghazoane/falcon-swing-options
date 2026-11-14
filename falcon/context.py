from __future__ import annotations

from .market import load_history


def summarize_market_context() -> dict[str, str]:
    """Summarize broad-market ETF context when provider data is available."""
    symbols = ("SPY", "QQQ", "^VIX")
    observations: list[str] = []
    for symbol in symbols:
        try:
            data = load_history(symbol, period="3mo", interval="1d")
            if data.empty or len(data) < 2:
                observations.append(f"{symbol}: غير متاح")
                continue
            change = (data["Close"].iloc[-1] / data["Close"].iloc[-2] - 1) * 100
            observations.append(f"{symbol}: {change:+.2f}% (آخر جلستين متاحتين)")
        except Exception:
            observations.append(f"{symbol}: غير متاح")
    return {
        "message": " | ".join(observations),
        "data_note": "مؤشرات سياق تقريبية من بيانات تاريخية؛ SPY وQQQ بدائل متابعة وليسا بديلاً مطابقاً لمؤشري SPX وNasdaq-100. لا تتوفر هنا تغذية أخبار أو بيانات فيدرالية لحظية.",
    }
