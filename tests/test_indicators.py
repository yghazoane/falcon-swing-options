import pandas as pd

from falcon.indicators import add_indicators


def test_indicator_columns_are_created():
    idx = pd.date_range("2024-01-01", periods=260, freq="B")
    close = pd.Series(range(100, 360), index=idx, dtype=float)
    data = pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1000}, index=idx)
    result = add_indicators(data)
    for column in ("EMA20", "EMA50", "EMA200", "RSI14", "MACD", "MACDSignal", "ATR14"):
        assert column in result.columns
    assert result["EMA20"].notna().any()
    assert result["ATR14"].notna().any()
