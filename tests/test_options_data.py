import pandas as pd

from falcon.options_data import normalize_option_chain


def test_normalize_option_chain_preserves_provider_values_and_side():
    source = pd.DataFrame([{
        "contractSymbol": "SPY261218C00600000",
        "strike": 600.0,
        "bid": 2.1,
        "ask": 2.2,
        "openInterest": 123,
    }])
    result = normalize_option_chain(source, "CALL")
    assert result.loc[0, "side"] == "CALL"
    assert result.loc[0, "strike"] == 600.0
    assert result.loc[0, "bid"] == 2.1
    assert pd.isna(result.loc[0, "impliedVolatility"])


def test_normalize_empty_chain_returns_expected_columns():
    result = normalize_option_chain(pd.DataFrame(), "PUT")
    assert result.empty
    assert "side" in result.columns
    assert "strike" in result.columns
