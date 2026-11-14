from __future__ import annotations

import pandas as pd


def rank_contract_data_quality(
    chain: pd.DataFrame,
    *,
    min_premium: float = 0.0,
    max_premium: float = 4.0,
    max_spread_pct: float = 20.0,
    min_volume: int = 10,
    min_open_interest: int = 100,
    min_days_to_expiry: float = 7.0,
    max_days_to_expiry: float = 60.0,
) -> pd.DataFrame:
    """Rank a provider chain by snapshot completeness and market-data quality.

    This is a neutral paper-research screen. It does not assess direction,
    expected return, probability of profit, or whether a contract should be bought.
    """
    if min_premium < 0 or max_premium < min_premium:
        raise ValueError("premium bounds must be non-negative and ordered")
    if max_spread_pct < 0 or min_volume < 0 or min_open_interest < 0:
        raise ValueError("spread, volume and open-interest thresholds cannot be negative")
    if min_days_to_expiry < 0 or max_days_to_expiry < min_days_to_expiry:
        raise ValueError("expiration-day bounds must be non-negative and ordered")

    if chain.empty:
        result = chain.copy()
        result["data_quality_score"] = pd.Series(dtype="float64")
        result["screen_status"] = pd.Series(dtype="object")
        result["screen_reasons"] = pd.Series(dtype="object")
        return result

    result = chain.copy()
    for column in ("mid", "spread_pct_mid", "volume", "openInterest", "impliedVolatility", "daysToExpiry"):
        if column not in result:
            result[column] = pd.NA
        result[column] = pd.to_numeric(result[column], errors="coerce")

    quote_valid = result.get(
        "quote_validity", pd.Series("", index=result.index)
    ).eq("عرض وطلب صالحان حسابياً") & result["mid"].gt(0)
    premium_ok = result["mid"].between(min_premium, max_premium, inclusive="both")
    spread_ok = result["spread_pct_mid"].between(0, max_spread_pct, inclusive="both")
    volume_ok = result["volume"].ge(min_volume)
    oi_ok = result["openInterest"].ge(min_open_interest)
    iv_ok = result["impliedVolatility"].gt(0)
    dte_ok = result["daysToExpiry"].between(
        min_days_to_expiry, max_days_to_expiry, inclusive="both"
    )

    spread_score = (
        (1 - result["spread_pct_mid"].clip(lower=0) / max(max_spread_pct, 1e-9)).clip(0, 1) * 25
    ).where(result["spread_pct_mid"].notna(), 0)
    result["data_quality_score"] = (
        quote_valid.astype(float) * 10
        + premium_ok.astype(float) * 15
        + spread_score
        + volume_ok.astype(float) * 15
        + oi_ok.astype(float) * 15
        + iv_ok.astype(float) * 10
        + dte_ok.astype(float) * 10
    ).round(1)

    reason_map = [
        (quote_valid, "عرض وطلب صالحان حسابياً"),
        (premium_ok, "السعر الوسطي ضمن النطاق"),
        (spread_ok, "السبريد ضمن الحد"),
        (volume_ok, "الحجم يحقق الحد"),
        (oi_ok, "العقود المفتوحة تحقق الحد"),
        (iv_ok, "التقلب الضمني متاح"),
        (dte_ok, "الأيام للانتهاء ضمن النطاق"),
    ]
    reasons = []
    for idx in result.index:
        passed = [label for mask, label in reason_map if bool(mask.loc[idx])]
        failed = [label for mask, label in reason_map if not bool(mask.loc[idx])]
        reasons.append("متحقق: " + "؛ ".join(passed) + " | غير متحقق: " + "؛ ".join(failed))

    result["screen_reasons"] = reasons
    all_filters = quote_valid & premium_ok & spread_ok & volume_ok & oi_ok & iv_ok & dte_ok
    result["screen_status"] = all_filters.map({
        True: "مطابق لمرشحات جودة البيانات",
        False: "لا يطابق جميع مرشحات جودة البيانات",
    })
    return result.sort_values(
        ["screen_status", "data_quality_score", "openInterest", "volume"],
        ascending=[True, False, False, False],
        na_position="last",
    )
