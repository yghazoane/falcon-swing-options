import numpy as np
import pandas as pd
import pytest

from falcon.stock_analysis import analyze_stock_frame


def sample_history(rows: int = 260) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=rows, freq="B")
    close = pd.Series(np.linspace(50, 100, rows), index=index)
    return pd.DataFrame({
        "Open": close - 0.2,
        "High": close + 1.0,
        "Low": close - 1.0,
        "Close": close,
        "Volume": 100_000,
    }, index=index)


def test_analyze_stock_frame_returns_core_fields():
    report = analyze_stock_frame(sample_history())
    assert report["last_close"] == pytest.approx(100.0)
    assert report["ema"]["ema20"] is not None
    assert report["ema"]["ema50"] is not None
    assert report["ema"]["ema200"] is not None
    assert report["rsi14"] is not None
    assert report["scenario_ranges"]["upper_1atr"] > report["last_close"]
    assert report["scenario_ranges"]["lower_1atr"] < report["last_close"]


def test_short_history_reports_missing_long_ema_without_crashing():
    report = analyze_stock_frame(sample_history(40))
    assert report["ema"]["ema20"] is not None
    assert report["ema"]["ema200"] is None
    assert report["descriptive_state"] in {
        "بيانات غير كافية للحكم", "ميل فني إيجابي متوافق نسبياً",
        "ميل فني سلبي متوافق نسبياً", "قراءة مختلطة / انتقالية"
    }


def test_missing_ohlc_columns_raise_clear_error():
    with pytest.raises(ValueError, match="Missing required columns"):
        analyze_stock_frame(pd.DataFrame({"Close": [1, 2, 3]}))


def test_empty_history_raises_clear_error():
    empty = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    with pytest.raises(ValueError, match="No usable OHLC rows"):
        analyze_stock_frame(empty)
