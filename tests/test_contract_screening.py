import pandas as pd
import pytest

from falcon.contract_screening import rank_contract_data_quality


def sample_chain():
    return pd.DataFrame([
        {
            "contractSymbol": "GOOD",
            "mid": 2.0,
            "spread_pct_mid": 10.0,
            "volume": 100,
            "openInterest": 500,
            "impliedVolatility": 0.3,
            "daysToExpiry": 30,
            "quote_validity": "عرض وطلب صالحان حسابياً",
        },
        {
            "contractSymbol": "WIDE",
            "mid": 2.0,
            "spread_pct_mid": 45.0,
            "volume": 100,
            "openInterest": 500,
            "impliedVolatility": 0.3,
            "daysToExpiry": 30,
            "quote_validity": "عرض وطلب صالحان حسابياً",
        },
    ])


def test_ranks_data_quality_and_explains_each_filter():
    result = rank_contract_data_quality(sample_chain())
    good = result.set_index("contractSymbol").loc["GOOD"]
    wide = result.set_index("contractSymbol").loc["WIDE"]
    assert good["data_quality_score"] > wide["data_quality_score"]
    assert good["screen_status"] == "مطابق لمرشحات جودة البيانات"
    assert "السبريد ضمن الحد" in good["screen_reasons"]
    assert wide["screen_status"] == "لا يطابق جميع مرشحات جودة البيانات"


def test_missing_or_invalid_quotes_never_pass():
    chain = sample_chain()
    chain.loc[0, "quote_validity"] = "غير مكتمل أو غير صالح"
    result = rank_contract_data_quality(chain)
    good = result.set_index("contractSymbol").loc["GOOD"]
    assert good["screen_status"] == "لا يطابق جميع مرشحات جودة البيانات"


def test_empty_chain_is_safe():
    result = rank_contract_data_quality(pd.DataFrame())
    assert result.empty
    assert "data_quality_score" in result.columns


def test_invalid_thresholds_raise():
    with pytest.raises(ValueError):
        rank_contract_data_quality(sample_chain(), min_premium=5, max_premium=2)
