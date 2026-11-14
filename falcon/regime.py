from __future__ import annotations

import pandas as pd
from .market import load_history

CORE_MARKETS = {
    "^GSPC": "S&P 500 Index",
    "SPY": "S&P 500 ETF proxy",
    "^NDX": "Nasdaq-100 Index",
    "QQQ": "Nasdaq-100 ETF proxy",
    "DIA": "Dow Jones ETF",
    "IWM": "Russell 2000 ETF",
    "^VIX": "VIX volatility index",
}
SECTORS = {
    "XLK": "Technology", "XLF": "Financials", "XLE": "Energy",
    "XLV": "Health Care", "XLI": "Industrials", "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples", "XLB": "Materials", "XLU": "Utilities",
    "XLRE": "Real Estate", "XLC": "Communication Services",
}
MACRO_PROXIES = {
    "^TNX": "US 10Y Treasury yield proxy",
    "DX-Y.NYB": "US Dollar Index proxy",
    "GC=F": "Gold futures proxy",
    "CL=F": "WTI crude oil futures proxy",
}

def _pct_change(series: pd.Series, periods: int) -> float | None:
    if len(series) <= periods or pd.isna(series.iloc[-periods - 1]) or series.iloc[-periods - 1] == 0:
        return None
    return float((series.iloc[-1] / series.iloc[-periods - 1] - 1) * 100)

def _trend(data: pd.DataFrame) -> str:
    if len(data) < 50:
        return "بيانات غير كافية"
    close = data["Close"]
    ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
    if close.iloc[-1] > ema20 > ema50:
        return "ميل صاعد"
    if close.iloc[-1] < ema20 < ema50:
        return "ميل هابط"
    return "مختلط/انتقالي"

def _row(symbol: str, label: str, period: str = "6mo") -> dict[str, object]:
    try:
        data = load_history(symbol, period=period, interval="1d")
        if data.empty:
            raise ValueError("empty")
        close = data["Close"]
        return {
            "symbol": symbol, "name": label, "last": float(close.iloc[-1]),
            "change_1d_pct": _pct_change(close, 1),
            "change_5d_pct": _pct_change(close, 5),
            "trend": _trend(data),
            "status": "available",
        }
    except Exception:
        return {"symbol": symbol, "name": label, "last": None,
                "change_1d_pct": None, "change_5d_pct": None,
                "trend": "غير متاح", "status": "unavailable"}

def market_dashboard() -> dict[str, list[dict[str, object]]]:
    """Return direct index series separately from ETF proxy series."""
    return {
        "indices": [_row(s, n) for s, n in CORE_MARKETS.items()],
        "sectors": [_row(s, n) for s, n in SECTORS.items()],
        "macro": [_row(s, n) for s, n in MACRO_PROXIES.items()],
    }

def compare_timeframes(symbol: str) -> list[dict[str, object]]:
    """Compare daily, hourly and derived 4-hour bars; 4h is resampled from hourly."""
    results: list[dict[str, object]] = []
    try:
        daily = load_history(symbol, period="1y", interval="1d")
        results.append({"timeframe": "1D", "trend": _trend(daily) if not daily.empty else "غير متاح",
                        "bars": len(daily), "source": "Daily provider bars"})
    except Exception:
        results.append({"timeframe": "1D", "trend": "غير متاح", "bars": 0, "source": "Unavailable"})
    try:
        hourly = load_history(symbol, period="60d", interval="1h")
        results.append({"timeframe": "1H", "trend": _trend(hourly) if not hourly.empty else "غير متاح",
                        "bars": len(hourly), "source": "Hourly provider bars"})
        if not hourly.empty:
            four_hour = hourly.resample("4h").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum"
            }).dropna(subset=["Open", "High", "Low", "Close"])
            results.append({"timeframe": "4H derived", "trend": _trend(four_hour),
                            "bars": len(four_hour), "source": "Resampled from 1H; not provider-native"})
        else:
            results.append({"timeframe": "4H derived", "trend": "غير متاح", "bars": 0,
                            "source": "Hourly history unavailable"})
    except Exception:
        results.extend([
            {"timeframe": "1H", "trend": "غير متاح", "bars": 0, "source": "Unavailable"},
            {"timeframe": "4H derived", "trend": "غير متاح", "bars": 0, "source": "Unavailable"},
        ])
    return results
