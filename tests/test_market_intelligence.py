import pandas as pd

from falcon.market_intelligence import _safe_change, _snapshot, build_market_intelligence


def test_safe_change_requires_enough_history():
    values = pd.Series([100.0, 102.0, 104.0])
    assert _safe_change(values, 1) == (104 / 102 - 1) * 100
    assert _safe_change(values, 3) is None


def test_snapshot_returns_unavailable_shape_when_provider_fails(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("offline")
    monkeypatch.setattr("falcon.market_intelligence.load_history", fail)
    result = _snapshot("SPY", "S&P 500 ETF proxy")
    assert result["status"] == "unavailable"
    assert result["last"] is None
    assert result["trend"] == "غير متاح"


def test_market_intelligence_has_explicit_data_quality_and_regime(monkeypatch):
    def fake_snapshot(symbol, label):
        if symbol in ("SPY", "QQQ"):
            return {
                "symbol": symbol, "name": label, "last": 100.0,
                "change_1d_pct": 1.0, "change_5d_pct": 2.0, "change_20d_pct": 4.0,
                "ema20": 99.0, "ema50": 98.0, "ema200": 95.0,
                "trend": "صاعد", "above_ema50": True, "above_ema200": True,
                "as_of": "2026-11-13", "bars": 250, "status": "available",
            }
        if symbol == "^VIX":
            return {"symbol": symbol, "name": label, "last": 16.0, "change_1d_pct": 0.0,
                    "change_5d_pct": 0.0, "change_20d_pct": 0.0, "ema20": 16.0,
                    "ema50": 16.0, "ema200": 16.0, "trend": "مختلط",
                    "above_ema50": False, "above_ema200": False, "as_of": "2026-11-13",
                    "bars": 250, "status": "available"}
        return {"symbol": symbol, "name": label, "last": 10.0, "change_1d_pct": 0.1,
                "change_5d_pct": 0.5, "change_20d_pct": 1.0, "ema20": 10.0,
                "ema50": 10.0, "ema200": 10.0, "trend": "مختلط",
                "above_ema50": True, "above_ema200": True, "as_of": "2026-11-13",
                "bars": 250, "status": "available"}
    monkeypatch.setattr("falcon.market_intelligence._snapshot", fake_snapshot)
    result = build_market_intelligence()
    assert result["regime"] == "ميل داعم للمخاطرة"
    assert result["confidence"] == "متوسطة"
    assert result["sector_participation"]["available_sectors"] > 0
    assert "تاريخية" in result["data_note"]
