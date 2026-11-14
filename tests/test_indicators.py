import pandas as pd
import numpy as np
import pytest
from falcon.indicators import add_indicators
from falcon.structure import add_confirmed_pivots
from falcon.fibonacci import latest_fibonacci_levels
from falcon.regime import _trend, _pct_change
from falcon.universe import parse_symbol_directories
from falcon.volume_profile import volume_by_price

def sample_data():
    idx = pd.date_range("2024-01-01", periods=260, freq="B")
    close = pd.Series(range(100, 360), index=idx, dtype=float)
    return pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1000}, index=idx)

def test_indicator_columns_and_rsi_edge_case():
    result = add_indicators(sample_data())
    for col in ("EMA20", "EMA50", "EMA200", "RSI14", "MACD", "MACDSignal", "ATR14", "VWAP"):
        assert col in result.columns
    assert result["EMA20"].notna().any()
    assert result["ATR14"].notna().any()
    assert result["RSI14"].dropna().iloc[-1] == 100
    assert result["VWAP"].notna().all()

def test_intraday_vwap_resets_each_session():
    idx = pd.date_range("2024-01-02 14:30", periods=4, freq="h", tz="UTC")
    idx = idx.append(pd.date_range("2024-01-03 14:30", periods=2, freq="h", tz="UTC"))
    close = pd.Series([10, 12, 14, 16, 20, 22], index=idx, dtype=float)
    data = pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 100}, index=idx)
    result = add_indicators(data)
    assert result["VWAP"].iloc[0] == pytest.approx(10)
    assert result["VWAP"].iloc[4] == pytest.approx(20)

def test_volume_profile_preserves_total_volume():
    profile = volume_by_price(sample_data(), bins=12)
    assert profile["volume"].sum() == sample_data()["Volume"].sum()

def test_pivots_wait_for_right_side_confirmation():
    result = add_confirmed_pivots(sample_data(), window=3)
    assert result["PivotHigh"].iloc[-3:].isna().all()
    assert result["PivotLow"].iloc[-3:].isna().all()

def test_fibonacci_handles_insufficient_swings():
    result = latest_fibonacci_levels(sample_data(), window=3)
    assert result["levels"] == {}
    assert result["extensions"] == {}

def test_fibonacci_returns_retracements_and_extensions_for_swing_data():
    idx = pd.date_range("2024-01-01", periods=120, freq="B")
    close = pd.Series(20 + np.sin(np.linspace(0, 15, 120)) * 4 + np.linspace(0, 2, 120), index=idx)
    data = pd.DataFrame({"Open": close, "High": close + 0.5, "Low": close - 0.5, "Close": close, "Volume": 1000}, index=idx)
    result = latest_fibonacci_levels(data, window=2)
    assert result["levels"]
    assert set(result["extensions"]) == {"1.272", "1.618", "2.000"}

def test_trend_classification_on_rising_series():
    assert _trend(sample_data()) == "ميل صاعد"

def test_pct_change_requires_enough_history():
    assert _pct_change(pd.Series([10.0, 11.0]), 1) == pytest.approx(10.0)
    assert _pct_change(pd.Series([10.0]), 1) is None

def test_symbol_directory_parser_excludes_test_issues_and_normalizes_symbols():
    nasdaq = "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\nAAA|Alpha Inc|Q|N|N|100|N|N\nBAD|Test Corp|Q|Y|N|100|N|N\nFile Creation Time: now|||||||"
    other = "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\nBRK.B|Berkshire Class B|N|BRK.B|N|100|N|BRK.B\nFile Creation Time: now|||||||"
    result = parse_symbol_directories(nasdaq, other)
    assert result["symbol"].tolist() == ["AAA", "BRK-B"]
