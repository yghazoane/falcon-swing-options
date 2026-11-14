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


def test_market_intelligence_prefers_direct_indices_and_avoids_double_count(monkeypatch):
    def row(symbol, above=True, status="available", last=100.0):
        return {
            "symbol": symbol, "name": symbol, "last": last if status == "available" else None,
            "change_1d_pct": 1.0, "change_5d_pct": 2.0, "change_20d_pct": 4.0,
            "ema20": 99.0, "ema50": 98.0, "ema200": 95.0,
            "trend": "صاعد" if above else "هابط", "above_ema50": above,
            "above_ema200": above, "as_of": "2026-11-13" if status == "available" else None,
            "bars": 250 if status == "available" else 0, "status": status,
        }

    def fake_snapshot(symbol, label):
        if symbol in ("^GSPC", "^NDX"):
            return row(symbol, above=True)
        if symbol == "SPY":
            return row(symbol, above=False)  # Must not override available direct index.
        if symbol == "QQQ":
            return row(symbol, above=False)
        if symbol == "^VIX":
            return row(symbol, last=16.0)
        return row(symbol)

    monkeypatch.setattr("falcon.market_intelligence._snapshot", fake_snapshot)
    result = build_market_intelligence()
    assert result["regime"] == "ميل داعم للمخاطرة"
    assert result["confidence"] == "متوسطة"
    assert [item["symbol"] for item in result["selected_benchmarks"]] == ["^GSPC", "^NDX"]
    assert all(item["basis"] == "مؤشر مباشر" for item in result["selected_benchmarks"])
    assert result["sector_participation"]["available_sectors"] > 0


def test_market_intelligence_uses_etf_proxy_only_when_direct_index_missing(monkeypatch):
    def row(symbol, above=True, status="available", last=100.0):
        return {
            "symbol": symbol, "name": symbol, "last": last if status == "available" else None,
            "change_1d_pct": 1.0, "change_5d_pct": 2.0, "change_20d_pct": 4.0,
            "ema20": 99.0, "ema50": 98.0, "ema200": 95.0,
            "trend": "صاعد" if above else "هابط", "above_ema50": above,
            "above_ema200": above, "as_of": "2026-11-13" if status == "available" else None,
            "bars": 250 if status == "available" else 0, "status": status,
        }

    def fake_snapshot(symbol, label):
        if symbol == "^GSPC":
            return row(symbol, status="unavailable")
        if symbol == "^NDX":
            return row(symbol, above=True)
        if symbol == "SPY":
            return row(symbol, above=True)
        if symbol == "QQQ":
            return row(symbol, above=False)
        if symbol == "^VIX":
            return row(symbol, last=16.0)
        return row(symbol)

    monkeypatch.setattr("falcon.market_intelligence._snapshot", fake_snapshot)
    result = build_market_intelligence()
    assert result["regime"] == "ميل داعم للمخاطرة"
    assert result["confidence"] == "متوسطة"
    assert result["selected_benchmarks"][0]["symbol"] == "SPY"
    assert result["selected_benchmarks"][0]["basis"] == "بديل ETF عند غياب المؤشر المباشر"
    assert result["selected_benchmarks"][1]["symbol"] == "^NDX"
