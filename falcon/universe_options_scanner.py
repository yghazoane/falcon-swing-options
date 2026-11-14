from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from .contract_screening import rank_contract_data_quality
from .market import load_history
from .market_intelligence import build_market_intelligence
from .multi_timeframe import load_multi_timeframe
from .options_data import get_option_expirations, load_options_chain, _days_to_expiry
from .research_ranking import rank_paper_candidates
from .stock_analysis import analyze_stock_frame


@st.cache_data(ttl=900, show_spinner=False)
def _cached_expirations(symbol: str) -> list[str]:
    return get_option_expirations(symbol)


@st.cache_data(ttl=120, show_spinner=False)
def _cached_chain(symbol: str, expiry: str, spot: float, rate: float) -> dict[str, Any]:
    return load_options_chain(symbol, expiry, spot, rate)


def scan_paper_universe(
    symbols: list[str],
    *,
    target_dte: int = 30,
    min_dte: int = 7,
    max_dte: int = 60,
    min_premium: float = 0.0,
    max_premium: float = 4.0,
    max_spread_pct: float = 20.0,
    min_volume: int = 10,
    min_open_interest: int = 100,
    risk_free_rate: float = 0.04,
    top_n_per_symbol: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Scan a small user-selected universe for paper-research candidates.

    Results are historical/provider snapshots and research-fit rankings only.
    No live order routing, trade recommendation, or profit probability is produced.
    """
    normalized = list(dict.fromkeys(s.strip().upper() for s in symbols if s.strip()))
    if not normalized:
        raise ValueError("At least one symbol is required")
    if len(normalized) > 8:
        raise ValueError("Scan up to 8 symbols at a time")
    if not min_dte <= target_dte <= max_dte:
        raise ValueError("target_dte must be inside the selected DTE range")

    market_context = build_market_intelligence()
    candidate_frames: list[pd.DataFrame] = []
    diagnostics: list[dict[str, Any]] = []

    for symbol in normalized:
        row: dict[str, Any] = {
            "symbol": symbol,
            "status": "لم يبدأ",
            "expiry": None,
            "contracts_checked": 0,
            "candidates_found": 0,
            "note": "",
        }
        try:
            expirations = _cached_expirations(symbol)
            eligible_expiries = []
            for expiry in expirations:
                try:
                    dte = _days_to_expiry(expiry)
                except ValueError:
                    continue
                if min_dte <= dte <= max_dte:
                    eligible_expiries.append((abs(dte - target_dte), expiry))
            if not eligible_expiries:
                row.update(status="لا يوجد انتهاء ضمن النطاق", note="لم يعثر المصدر على تاريخ انتهاء ضمن حدود DTE المحددة.")
                diagnostics.append(row)
                continue
            _, expiry = min(eligible_expiries)
            row["expiry"] = expiry

            spot_history = load_history(symbol, period="5d", interval="1d")
            if spot_history.empty or spot_history["Close"].dropna().empty:
                row.update(status="السعر المرجعي غير متاح", note="لم تصل بيانات سعر أساسية صالحة.")
                diagnostics.append(row)
                continue
            spot = float(spot_history["Close"].dropna().iloc[-1])

            daily_history = load_history(symbol, period="1y", interval="1d")
            if daily_history.empty:
                row.update(status="التحليل الفني غير متاح", note="لا تتوفر بيانات يومية كافية.")
                diagnostics.append(row)
                continue
            stock_report = analyze_stock_frame(daily_history)
            _, timeframe_alignment = load_multi_timeframe(symbol)

            snapshot = _cached_chain(symbol, expiry, spot, risk_free_rate)
            screened_calls = rank_contract_data_quality(
                snapshot["calls"], min_premium=min_premium, max_premium=max_premium,
                max_spread_pct=max_spread_pct, min_volume=min_volume,
                min_open_interest=min_open_interest,
                min_days_to_expiry=min_dte, max_days_to_expiry=max_dte,
            )
            screened_puts = rank_contract_data_quality(
                snapshot["puts"], min_premium=min_premium, max_premium=max_premium,
                max_spread_pct=max_spread_pct, min_volume=min_volume,
                min_open_interest=min_open_interest,
                min_days_to_expiry=min_dte, max_days_to_expiry=max_dte,
            )
            row["contracts_checked"] = len(screened_calls) + len(screened_puts)

            ranked = rank_paper_candidates(
                screened_calls, screened_puts,
                market_context=market_context,
                stock_report=stock_report,
                timeframe_alignment=timeframe_alignment,
                top_n=top_n_per_symbol,
            )
            if ranked.empty:
                row.update(status="لا توجد عقود مطابقة", note="لم تجتز أي صفوف جميع مرشحات جودة البيانات.")
            else:
                ranked["symbol"] = symbol
                ranked["expiry"] = expiry
                ranked["spot_reference"] = spot
                candidate_frames.append(ranked)
                row.update(
                    status="اكتمل الفحص",
                    candidates_found=len(ranked),
                    note=f"السياق الفني: {stock_report['descriptive_state']} · توافق الأطر: {timeframe_alignment['label']}",
                )
        except Exception as exc:
            row.update(status="تعذر الفحص", note=f"{type(exc).__name__}: {exc}")
        diagnostics.append(row)

    candidates = (
        pd.concat(candidate_frames, ignore_index=True)
        if candidate_frames else pd.DataFrame()
    )
    if not candidates.empty:
        candidates = candidates.sort_values(
            ["research_fit_score", "data_quality_score", "openInterest", "volume"],
            ascending=[False, False, False, False],
            na_position="last",
        ).reset_index(drop=True)
    return candidates, pd.DataFrame(diagnostics), market_context
