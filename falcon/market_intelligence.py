from __future__ import annotations

from typing import Any

import pandas as pd

from .market import load_history
from .regime import CORE_MARKETS, MACRO_PROXIES, SECTORS


def _safe_change(close: pd.Series, periods: int) -> float | None:
    if len(close) <= periods:
        return None
    base = float(close.iloc[-periods - 1])
    if base == 0:
        return None
    return (float(close.iloc[-1]) / base - 1.0) * 100.0


def _snapshot(symbol: str, label: str) -> dict[str, Any]:
    try:
        frame = load_history(symbol, period="1y", interval="1d")
        if frame.empty:
            raise ValueError("empty history")
        close = frame["Close"].dropna()
        last = float(close.iloc[-1])
        ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
        ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
        ema200 = (
            float(close.ewm(span=200, adjust=False).mean().iloc[-1])
            if len(close) >= 200 else None
        )
        if last > ema20 > ema50 and (ema200 is None or ema50 > ema200):
            trend = "صاعد"
        elif last < ema20 < ema50 and (ema200 is None or ema50 < ema200):
            trend = "هابط"
        else:
            trend = "مختلط / انتقالي"
        return {
            "symbol": symbol,
            "name": label,
            "last": last,
            "change_1d_pct": _safe_change(close, 1),
            "change_5d_pct": _safe_change(close, 5),
            "change_20d_pct": _safe_change(close, 20),
            "ema20": ema20,
            "ema50": ema50,
            "ema200": ema200,
            "trend": trend,
            "above_ema50": last > ema50,
            "above_ema200": last > ema200 if ema200 is not None else None,
            "as_of": str(close.index[-1]),
            "bars": len(close),
            "status": "available",
        }
    except Exception:
        return {
            "symbol": symbol, "name": label, "last": None,
            "change_1d_pct": None, "change_5d_pct": None, "change_20d_pct": None,
            "ema20": None, "ema50": None, "ema200": None, "trend": "غير متاح",
            "above_ema50": None, "above_ema200": None, "as_of": None,
            "bars": 0, "status": "unavailable",
        }


def _select_benchmark(primary: dict[str, Any], proxy: dict[str, Any]) -> dict[str, Any] | None:
    """Prefer the direct index; use its ETF only when direct index data is unavailable."""
    if primary.get("status") == "available":
        return {**primary, "basis": "مؤشر مباشر"}
    if proxy.get("status") == "available":
        return {**proxy, "basis": "بديل ETF عند غياب المؤشر المباشر"}
    return None


def build_market_intelligence() -> dict[str, Any]:
    """Build a descriptive cross-asset market snapshot; never a trade signal."""
    index_symbols = ("^GSPC", "^NDX", "SPY", "QQQ", "DIA", "IWM", "^VIX")
    indices = [_snapshot(symbol, CORE_MARKETS[symbol]) for symbol in index_symbols]
    sectors = [_snapshot(symbol, label) for symbol, label in SECTORS.items()]
    macro = [_snapshot(symbol, label) for symbol, label in MACRO_PROXIES.items()]

    by_symbol = {row["symbol"]: row for row in indices}
    benchmark_pairs = (
        ("^GSPC", "SPY", "S&P 500"),
        ("^NDX", "QQQ", "Nasdaq-100"),
    )
    selected_benchmarks = []
    for direct_symbol, proxy_symbol, label in benchmark_pairs:
        selected = _select_benchmark(by_symbol[direct_symbol], by_symbol[proxy_symbol])
        if selected is not None:
            selected_benchmarks.append({**selected, "benchmark": label})

    spy = by_symbol.get("SPY", {})
    vix = by_symbol.get("^VIX", {})
    vix_value = vix.get("last") if vix.get("status") == "available" else None

    if len(selected_benchmarks) < 2:
        regime = "غير محسوم — بيانات المؤشرات غير مكتملة"
        confidence = "منخفضة"
    else:
        bullish = all(row["above_ema50"] for row in selected_benchmarks)
        bearish = all(not row["above_ema50"] for row in selected_benchmarks)
        if bullish and vix_value is not None and vix_value < 20:
            regime, confidence = "ميل داعم للمخاطرة", "متوسطة"
        elif bearish and vix_value is not None and vix_value >= 25:
            regime, confidence = "ميل حذر / تجنب المخاطرة", "متوسطة"
        elif bullish:
            regime, confidence = "ميل صاعد مع تقلب يحتاج متابعة", "منخفضة"
        elif bearish:
            regime, confidence = "ميل هابط مع تقلب يحتاج متابعة", "منخفضة"
        else:
            regime, confidence = "سوق مختلط / انتقالي", "منخفضة"

    sector_available = [row for row in sectors if row["status"] == "available"]
    sector_positive = sum((row["change_20d_pct"] or 0) > 0 for row in sector_available)
    sector_negative = sum((row["change_20d_pct"] or 0) < 0 for row in sector_available)
    spy_return = spy.get("change_20d_pct")
    for row in sectors:
        row["relative_20d_pct"] = (
            row["change_20d_pct"] - spy_return
            if row["change_20d_pct"] is not None and spy_return is not None else None
        )

    latest_dates = [row["as_of"] for row in indices + sectors + macro if row["as_of"]]
    benchmark_basis = " · ".join(
        f"{row['benchmark']}: {row['symbol']} ({row['basis']})"
        for row in selected_benchmarks
    )
    return {
        "regime": regime,
        "confidence": confidence,
        "vix_level": vix_value,
        "indices": indices,
        "selected_benchmarks": selected_benchmarks,
        "benchmark_basis": benchmark_basis,
        "sectors": sectors,
        "macro": macro,
        "sector_participation": {
            "available_sectors": len(sector_available),
            "positive_20d": sector_positive,
            "negative_20d": sector_negative,
        },
        "latest_data_date": max(latest_dates) if latest_dates else None,
        "method_note": (
            "التصنيف الوصفي يستخدم S&P 500 وNasdaq-100 المباشرين عند توفرهما، "
            "ويستخدم SPY أو QQQ بديلاً عند تعذر المؤشر المباشر؛ لا يحتسب المؤشر وصندوقه مرتين. "
            "تُقارن القراءة بمتوسط EMA50 مع سياق VIX. حدود VIX (20 و25) تقريبية وليست تنبؤية."
        ),
        "data_note": (
            "المصدر Yahoo Finance عبر yfinance؛ بيانات تاريخية وقد تكون متأخرة أو ناقصة. "
            "SPY/QQQ بدائل متابعة وليسا مطابقين للمؤشرين. صناديق القطاعات تقيس أداء مجموعة صناديق "
            "ولا تمثل اتساعاً كاملاً لجميع الأسهم."
        ),
    }
