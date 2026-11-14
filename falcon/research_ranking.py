from __future__ import annotations

from typing import Any

import pandas as pd


MATCHED_STATUS = "مطابق لمرشحات جودة البيانات"


def _market_bias(regime: str) -> str:
    value = str(regime)
    if "داعم للمخاطرة" in value or "ميل صاعد" in value:
        return "bullish"
    if "حذر / تجنب المخاطرة" in value or "ميل هابط" in value:
        return "bearish"
    return "neutral"


def _technical_bias(state: str) -> str:
    value = str(state)
    if "إيجابي" in value:
        return "bullish"
    if "سلبي" in value:
        return "bearish"
    return "neutral"


def _timeframe_bias(label: str) -> str:
    value = str(label)
    if "اتساق صاعد" in value:
        return "bullish"
    if "اتساق هابط" in value:
        return "bearish"
    return "neutral"


def _alignment_points(context_bias: str, option_bias: str, weight: float) -> float:
    if context_bias == "neutral":
        return weight * 0.5
    return weight if context_bias == option_bias else 0.0


def rank_paper_candidates(
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    *,
    market_context: dict[str, Any],
    stock_report: dict[str, Any],
    timeframe_alignment: dict[str, Any],
    top_n: int = 10,
) -> pd.DataFrame:
    """Rank options rows for a paper-research watchlist using explainable alignment.

    The score is a weighted match to the selected research filters and context.
    It is not a probability, expected return, trading signal, or recommendation.
    """
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    market_bias = _market_bias(market_context.get("regime", ""))
    technical_bias = _technical_bias(stock_report.get("descriptive_state", ""))
    timeframe_bias = _timeframe_bias(timeframe_alignment.get("label", ""))
    volume_ratio = stock_report.get("volume_ratio_20")
    try:
        volume_ratio = float(volume_ratio) if volume_ratio is not None else None
    except (TypeError, ValueError):
        volume_ratio = None

    candidates: list[dict[str, Any]] = []
    for option_type, frame, option_bias in (
        ("CALL", calls, "bullish"),
        ("PUT", puts, "bearish"),
    ):
        if frame is None or frame.empty:
            continue
        for _, row in frame.iterrows():
            if row.get("screen_status") != MATCHED_STATUS:
                continue

            quality = pd.to_numeric(pd.Series([row.get("data_quality_score")]), errors="coerce").iloc[0]
            delta = pd.to_numeric(pd.Series([row.get("delta")]), errors="coerce").iloc[0]
            dte = pd.to_numeric(pd.Series([row.get("daysToExpiry")]), errors="coerce").iloc[0]
            if pd.isna(quality) or pd.isna(delta) or pd.isna(dte):
                continue

            market_points = _alignment_points(market_bias, option_bias, 20)
            technical_points = _alignment_points(technical_bias, option_bias, 25)
            timeframe_points = _alignment_points(timeframe_bias, option_bias, 15)
            quality_points = max(0.0, min(float(quality), 100.0)) * 0.20

            abs_delta = abs(float(delta))
            delta_points = 10.0 if 0.30 <= abs_delta <= 0.70 else 5.0 if 0.20 <= abs_delta <= 0.80 else 0.0
            dte_points = 5.0 if 14 <= float(dte) <= 45 else 3.0 if 7 <= float(dte) <= 60 else 0.0
            volume_points = 5.0 if volume_ratio is not None and volume_ratio >= 1.2 else (
                2.5 if volume_ratio is not None and volume_ratio >= 0.8 else 0.0
            )

            score = round(
                market_points + technical_points + timeframe_points
                + quality_points + delta_points + dte_points + volume_points,
                1,
            )
            reasons = [
                f"توافق السوق العام: {market_points:.1f}/20",
                f"توافق التحليل الفني للأصل: {technical_points:.1f}/25",
                f"توافق الأطر الزمنية: {timeframe_points:.1f}/15",
                f"جودة بيانات العقد: {quality_points:.1f}/20",
                f"نطاق Delta البحثي: {delta_points:.1f}/10",
                f"مدة الانتهاء: {dte_points:.1f}/5",
                f"تأكيد الحجم الأساسي: {volume_points:.1f}/5",
            ]
            label = (
                "توافق مرتفع مع معايير البحث" if score >= 80
                else "توافق متوسط مع معايير البحث" if score >= 65
                else "توافق محدود مع معايير البحث" if score >= 50
                else "توافق ضعيف مع معايير البحث"
            )
            item = row.to_dict()
            item.update({
                "option_type": option_type,
                "research_fit_score": score,
                "research_fit_label": label,
                "research_fit_reasons": "؛ ".join(reasons),
                "market_bias": market_bias,
                "underlying_bias": technical_bias,
                "timeframe_bias": timeframe_bias,
            })
            candidates.append(item)

    if not candidates:
        return pd.DataFrame(columns=[
            "option_type", "contractSymbol", "research_fit_score",
            "research_fit_label", "research_fit_reasons",
        ])
    result = pd.DataFrame(candidates)
    return result.sort_values(
        ["research_fit_score", "data_quality_score", "openInterest", "volume"],
        ascending=[False, False, False, False],
        na_position="last",
    ).head(top_n).reset_index(drop=True)
