import numpy as np
import pandas as pd

from falcon.multi_timeframe import analyze_timeframe, summarize_alignment


def sample_frame(periods=260, rising=True):
    idx = pd.date_range("2024-01-01", periods=periods, freq="B")
    values = np.linspace(100, 180, periods) if rising else np.linspace(180, 100, periods)
    close = pd.Series(values, index=idx)
    return pd.DataFrame({
        "Open": close - 0.2, "High": close + 1, "Low": close - 1,
        "Close": close, "Volume": 1000,
    }, index=idx)


def test_analyze_timeframe_reports_trend_indicators_and_source():
    result = analyze_timeframe(sample_frame(), "1D", "test fixture")
    assert result["timeframe"] == "1D"
    assert result["trend"] == "صاعد متوافق"
    assert result["rsi14"] is not None
    assert result["ema200"] is not None
    assert result["source"] == "test fixture"
    assert result["status"] == "available"


def test_analyze_timeframe_handles_insufficient_history():
    result = analyze_timeframe(sample_frame(20), "1H", "short fixture")
    assert result["status"] == "insufficient"
    assert result["trend"] == "بيانات غير كافية"


def test_alignment_detects_agreement_and_conflict():
    bullish = {"status": "available", "trend": "صاعد متوافق"}
    bearish = {"status": "available", "trend": "هابط متوسط"}
    mixed = {"status": "available", "trend": "مختلط / انتقالي"}
    assert summarize_alignment([bullish, bullish])["label"] == "اتساق صاعد بين الأطر المتاحة"
    assert summarize_alignment([bullish, bearish])["label"] == "تعارض بين الأطر الزمنية"
    assert summarize_alignment([mixed])["label"] == "اتجاه مختلط أو انتقالي"


def test_alignment_ignores_unavailable_timeframes():
    unavailable = {"status": "insufficient", "trend": "بيانات غير كافية"}
    bullish = {"status": "available", "trend": "صاعد متوسط"}
    result = summarize_alignment([unavailable, bullish])
    assert result["available_timeframes"] == 1
    assert result["label"] == "اتساق صاعد بين الأطر المتاحة"


def test_empty_data_returns_safe_placeholder():
    result = analyze_timeframe(pd.DataFrame(), "4H", "missing")
    assert result["status"] == "insufficient"
    assert result["close"] is None
