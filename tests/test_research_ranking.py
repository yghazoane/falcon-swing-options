import pandas as pd

from falcon.research_ranking import rank_paper_candidates


def candidate(option_type, delta):
    return pd.DataFrame([{
        "contractSymbol": f"TEST-{option_type}",
        "delta": delta,
        "daysToExpiry": 30,
        "data_quality_score": 90.0,
        "screen_status": "مطابق لمرشحات جودة البيانات",
        "openInterest": 500,
        "volume": 100,
        "mid": 2.0,
    }])


def test_bullish_context_ranks_call_above_put():
    result = rank_paper_candidates(
        candidate("C", 0.5),
        candidate("P", -0.5),
        market_context={"regime": "ميل داعم للمخاطرة"},
        stock_report={"descriptive_state": "ميل فني إيجابي متوافق نسبياً", "volume_ratio_20": 1.4},
        timeframe_alignment={"label": "اتساق صاعد بين الأطر المتاحة"},
    )
    assert result.iloc[0]["option_type"] == "CALL"
    assert result.iloc[0]["research_fit_score"] > result.iloc[1]["research_fit_score"]


def test_bearish_context_ranks_put_above_call():
    result = rank_paper_candidates(
        candidate("C", 0.5),
        candidate("P", -0.5),
        market_context={"regime": "ميل حذر / تجنب المخاطرة"},
        stock_report={"descriptive_state": "ميل فني سلبي متوافق نسبياً", "volume_ratio_20": 1.3},
        timeframe_alignment={"label": "اتساق هابط بين الأطر المتاحة"},
    )
    assert result.iloc[0]["option_type"] == "PUT"


def test_only_rows_passing_data_quality_filters_are_ranked():
    calls = candidate("C", 0.5)
    calls.loc[0, "screen_status"] = "لا يطابق جميع مرشحات جودة البيانات"
    result = rank_paper_candidates(
        calls, pd.DataFrame(),
        market_context={"regime": "سوق مختلط / انتقالي"},
        stock_report={"descriptive_state": "قراءة مختلطة / انتقالية"},
        timeframe_alignment={"label": "تعارض بين الأطر الزمنية"},
    )
    assert result.empty


def test_missing_direction_context_does_not_create_false_directional_edge():
    result = rank_paper_candidates(
        candidate("C", 0.5), candidate("P", -0.5),
        market_context={"regime": "غير محسوم"},
        stock_report={"descriptive_state": "قراءة مختلطة / انتقالية"},
        timeframe_alignment={"label": "تعارض بين الأطر الزمنية"},
    )
    assert result.iloc[0]["research_fit_score"] == result.iloc[1]["research_fit_score"]


def test_top_n_is_enforced_and_validated():
    calls = pd.concat([candidate(f"C{i}", 0.5) for i in range(3)], ignore_index=True)
    result = rank_paper_candidates(
        calls, pd.DataFrame(),
        market_context={"regime": "ميل داعم للمخاطرة"},
        stock_report={"descriptive_state": "ميل فني إيجابي متوافق نسبياً"},
        timeframe_alignment={"label": "اتساق صاعد"},
        top_n=2,
    )
    assert len(result) == 2
