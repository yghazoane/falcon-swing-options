import numpy as np
import pandas as pd
import pytest

from falcon.technical_analysis import analyze_stock_technicals


def sample_data(periods=260):
    idx = pd.date_range("2024-01-01", periods=periods, freq="B")
    close = pd.Series(np.linspace(100, 180, periods) + np.sin(np.arange(periods) / 5), index=idx)
    return pd.DataFrame({
        "Open": close - 0.2, "High": close + 1, "Low": close - 1,
        "Close": close, "Volume": 1000 + np.arange(periods) * 2,
    }, index=idx)


def test_integrated_technical_analysis_returns_explainable_components():
    result = analyze_stock_technicals(sample_data())
    assert result["status"] == "available"
    assert result["trend"] in {"ترتيب متوسطات صاعد", "ترتيب متوسطات هابط", "متداخل / انتقالي", "بيانات غير كافية"}
    assert result["atr"] is not None
    assert result["atr_pct"] > 0
    assert result["atr_scenarios"]["plus_1_atr"] > result["close"]
    assert result["structure"]["event_type"] in {"none", "bos_up", "bos_down", "choch_up", "choch_down"}
    assert result["fibonacci"]["levels"] is not None
    assert result["volume_profile_poc"] is not None
    assert "ليست أهدافاً" in result["note"]


def test_empty_data_returns_safe_unavailable_result():
    result = analyze_stock_technicals(pd.DataFrame())
    assert result["status"] == "unavailable"
    assert result["atr"] is None
    assert result["support"] is None


def test_invalid_pivot_window_is_rejected():
    with pytest.raises(ValueError):
        analyze_stock_technicals(sample_data(), pivot_window=0)


def test_short_history_keeps_missing_long_term_context_explicit():
    result = analyze_stock_technicals(sample_data(30))
    assert result["status"] == "available"
    assert result["indicators"]["ema200"] is None
