from types import SimpleNamespace

import pandas as pd
import pytest

from falcon import options_data


class FakeTicker:
    options = ["2027-01-15"]

    def __init__(self, symbol):
        self.symbol = symbol

    def option_chain(self, expiry):
        calls = pd.DataFrame([{
            "contractSymbol": "TEST270115C00100000",
            "strike": 100.0, "lastPrice": 4.0, "bid": 3.9, "ask": 4.1,
            "volume": 12, "openInterest": 150, "impliedVolatility": 0.25,
            "inTheMoney": False, "contractSize": "REGULAR", "currency": "USD",
        }])
        puts = pd.DataFrame(columns=calls.columns)
        return SimpleNamespace(calls=calls, puts=puts)


def test_load_options_chain_normalizes_quotes_and_calculates_greeks(monkeypatch):
    monkeypatch.setattr(options_data.yf, "Ticker", FakeTicker)
    result = options_data.load_options_chain("test", "2027-01-15", 100.0)
    assert result["symbol"] == "TEST"
    assert result["provider"] == "Yahoo Finance via yfinance"
    assert len(result["calls"]) == 1
    row = result["calls"].iloc[0]
    assert row["mid"] == pytest.approx(4.0)
    assert row["spread"] == pytest.approx(0.2)
    assert row["delta"] is not None
    assert result["puts"].empty


def test_rejects_unknown_expiration(monkeypatch):
    monkeypatch.setattr(options_data.yf, "Ticker", FakeTicker)
    with pytest.raises(ValueError, match="Selected expiration"):
        options_data.load_options_chain("TEST", "2027-02-19", 100.0)


def test_rejects_invalid_spot():
    with pytest.raises(ValueError, match="spot must be positive"):
        options_data.load_options_chain("TEST", "2027-01-15", 0)
