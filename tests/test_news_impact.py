from falcon.news_impact import classify_news_impact


def test_supportive_policy_cue_is_labeled_cautiously():
    result = classify_news_impact({"title": "Inflation cooled and rate cut discussed"})
    assert result["impact"] == "potentially_supportive"
    assert result["confidence"] in {"منخفضة", "متوسطة"}
    assert "rate cut" in result["reason"]


def test_adverse_policy_cue_is_labeled():
    result = classify_news_impact({"title": "Inflation remains elevated; higher for longer"})
    assert result["impact"] == "potentially_adverse"


def test_conflicting_cues_are_mixed_not_forced_directional():
    result = classify_news_impact({
        "title": "Rate cut discussed",
        "description": "Inflation remains elevated and uncertainty persists",
    })
    assert result["impact"] == "mixed_or_unclear"


def test_unknown_headline_defaults_to_neutral():
    result = classify_news_impact({"title": "Federal Reserve announces staff appointment"})
    assert result["impact"] == "neutral"
    assert result["confidence"] == "منخفضة"


def test_arabic_terms_are_supported():
    result = classify_news_impact({"title": "تباطؤ التضخم قد يدعم خفض الفائدة"})
    assert result["impact"] == "potentially_supportive"
