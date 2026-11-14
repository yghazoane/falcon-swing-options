import pandas as pd
import pytest

from falcon import universe_options_scanner as scanner


def fake_history():
    index = pd.date_range("2025-01-01", periods=220, freq="B")
    close = pd.Series(range(100, 320), index=index, dtype=float)
    return pd.DataFrame({
        "Open": close - 0.2, "High": close + 1,
        "Low": close - 1, "Close": close, "Volume": 1000,
    }, index=index)


def fake_chain():
    row = {
        "contractSymbol": "TEST-CALL",
        "mid": 2.0,
        "spread_pct_mid": 10.0,
        "volume": 100,
        "openInterest": 500,
        "impliedVolatility": 0.3,
        "daysToExpiry": 30,
        "delta": 0.5,
        "strike": 300.0,
        "lastPrice": 2.0,
        "bid": 1.9,
        "ask": 2.1,
        "quote_validity": "عرض وطلب صالحان حسابياً",
    }
    calls = pd.DataFrame([row])
    puts = pd.DataFrame([{**row, "contractSymbol": "TEST-PUT", "delta": -0.5}])
    return {"calls": calls, "puts": puts}


def setup_scanner(monkeypatch):
    monkeypatch.setattr(scanner, "build_market_intelligence", lambda: {
        "regime": "ميل داعم للمخاطرة", "confidence": "متوسطة",
        "latest_data_date": "2026-11-13", "data_note": "fixture",
    })
    monkeypatch.setattr(scanner, "_cached_expirations", lambda symbol: ["2026-12-15"])
    monkeypatch.setattr(scanner, "_days_to_expiry", lambda expiry: 30.0)
    monkeypatch.setattr(scanner, "load_history", lambda *args, **kwargs: fake_history())
    monkeypatch.setattr(scanner, "analyze_stock_frame", lambda frame: {
        "descriptive_state": "ميل فني إيجابي متوافق نسبياً",
        "volume_ratio_20": 1.4,
    })
    monkeypatch.setattr(scanner, "load_multi_timeframe", lambda symbol: ([], {
        "label": "اتساق صاعد بين الأطر المتاحة",
    }))
    monkeypatch.setattr(scanner, "_cached_chain", lambda *args: fake_chain())


def test_scans_multiple_symbols_and_returns_ranked_candidates(monkeypatch):
    setup_scanner(monkeypatch)
    candidates, diagnostics, context = scanner.scan_paper_universe(["AAA", "BBB"])
    assert set(candidates["symbol"]) == {"AAA", "BBB"}
    assert len(diagnostics) == 2
    assert diagnostics["status"].eq("اكتمل الفحص").all()
    assert context["regime"] == "ميل داعم للمخاطرة"
    assert candidates["research_fit_score"].is_monotonic_decreasing


def test_scanner_rejects_more_than_eight_symbols():
    with pytest.raises(ValueError, match="up to 8"):
        scanner.scan_paper_universe([f"S{i}" for i in range(9)])


def test_scanner_handles_symbols_without_expirations(monkeypatch):
    setup_scanner(monkeypatch)
    monkeypatch.setattr(scanner, "_cached_expirations", lambda symbol: [])
    candidates, diagnostics, _ = scanner.scan_paper_universe(["AAA"])
    assert candidates.empty
    assert diagnostics.iloc[0]["status"] == "لا يوجد انتهاء ضمن النطاق"


def test_scanner_rejects_target_outside_dte_range():
    with pytest.raises(ValueError, match="target_dte"):
        scanner.scan_paper_universe(["AAA"], target_dte=70, min_dte=7, max_dte=60)
