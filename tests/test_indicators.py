import pandas as pd
from falcon.indicators import add_indicators
from falcon.structure import add_confirmed_pivots
from falcon.fibonacci import latest_fibonacci_levels

def sample_data():
    idx = pd.date_range("2024-01-01", periods=260, freq="B")
    close = pd.Series(range(100, 360), index=idx, dtype=float)
    return pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1000}, index=idx)

def test_indicator_columns_and_rsi_edge_case():
    result = add_indicators(sample_data())
    for col in ("EMA20", "EMA50", "EMA200", "RSI14", "MACD", "MACDSignal", "ATR14"):
        assert col in result.columns
    assert result["EMA20"].notna().any()
    assert result["ATR14"].notna().any()
    assert result["RSI14"].dropna().iloc[-1] == 100

def test_pivots_wait_for_right_side_confirmation():
    result = add_confirmed_pivots(sample_data(), window=3)
    assert result["PivotHigh"].iloc[-3:].isna().all()
    assert result["PivotLow"].iloc[-3:].isna().all()

def test_fibonacci_handles_insufficient_swings():
    result = latest_fibonacci_levels(sample_data(), window=3)
    assert result["levels"] == {}
