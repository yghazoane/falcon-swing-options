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
    assert pd.notna(row["delta"])
    assert row["quote_validity"] == "عرض وطلب صالحان حسابياً"
    assert "not be synchronized" in result["spot_reference_warning"]
    assert result["puts"].empty


def test_invalid_bid_ask_are_not_used_for_mid(monkeypatch):
    class InvalidQuoteTicker(FakeTicker):
        def option_chain(self, expiry):
            result = super().option_chain(expiry)
            result.calls.loc[0, "ask"] = 3.5
            return result

    monkeypatch.setattr(options_data.yf, "Ticker", InvalidQuoteTicker)
    result = options_data.load_options_chain("TEST", "2027-01-15", 100.0)
    row = result["calls"].iloc[0]
    assert pd.isna(row["mid"])
    assert pd.isna(row["spread"])
    assert row["quote_validity"] == "غير مكتمل أو غير صالح"


@pytest.mark.parametrize("spot", [0, -1, float("nan"), float("inf")])
def test_rejects_invalid_spot(monkeypatch, spot):
    monkeypatch.setattr(options_data.yf, "Ticker", FakeTicker)
    with pytest.raises(ValueError, match="spot"):
        options_data.load_options_chain("TEST", "2027-01-15", spot)


def test_rejects_unknown_expiration(monkeypatch):
    monkeypatch.setattr(options_data.yf, "Ticker", FakeTicker)
    with pytest.raises(ValueError, match="Selected expiration"):
        options_data.load_options_chain("TEST", "2027-02-19", 100.0)


def test_expiry_days_use_new_york_close():
    now = options_data.datetime(2027, 1, 15, 15, 0, tzinfo=options_data.NEW_YORK)
    assert options_data._days_to_expiry("2027-01-15", now) == pytest.approx(1 / 24)
