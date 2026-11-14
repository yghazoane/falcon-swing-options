from __future__ import annotations

import pandas as pd
import streamlit as st

from falcon.auth import require_password
from falcon.universe_options_scanner import scan_paper_universe

st.set_page_config(page_title="Falcon · ماسح العقود البحثي", page_icon="🦅", layout="wide")
require_password()

st.title("ماسح العقود البحثي متعدد الرموز")
st.caption("يفحص مجموعة صغيرة من الرموز، ثم يرتب عقود CALL وPUT المطابقة لمرشحات البيانات وسياق السوق لأغراض قائمة مراقبة ومحاكاة بحثية.")

with st.sidebar:
    symbols_text = st.text_area(
        "الرموز المراد فحصها — افصل بينها بفواصل",
        value="SPY, QQQ, DIA, IWM, AAPL, MSFT, NVDA, AMZN",
        height=110,
    )
    st.caption("الحد الأقصى 8 رموز في كل عملية فحص لتقليل ضغط الطلبات على مزود البيانات.")
    st.subheader("اختيار الانتهاء")
    min_dte, max_dte = st.slider("نطاق DTE المسموح", 1, 120, (7, 60))
    target_dte = st.slider("DTE المستهدف لاختيار أقرب تاريخ انتهاء", min_dte, max_dte, min(30, max_dte))
    st.subheader("مرشحات جودة العقد")
    min_premium, max_premium = st.slider("نطاق Mid بالدولار", 0.0, 20.0, (0.0, 4.0), 0.1)
    max_spread = st.slider("أقصى سبريد %", 1, 100, 20)
    min_volume = st.number_input("أقل حجم تداول", min_value=0, value=10, step=10)
    min_oi = st.number_input("أقل Open Interest", min_value=0, value=100, step=50)
    rate_pct = st.number_input("معدل الفائدة المفترض %", min_value=-5.0, max_value=30.0, value=4.0, step=0.25)
    top_n = st.slider("أقصى عدد مرشحين لكل رمز", 1, 10, 5)
    run_scan = st.button("ابدأ فحص الرموز", type="primary", use_container_width=True)

symbols = [part.strip().upper() for part in symbols_text.replace("\n", ",").split(",") if part.strip()]
symbols = list(dict.fromkeys(symbols))

if run_scan:
    if not symbols:
        st.error("أدخل رمزاً واحداً على الأقل.")
    elif len(symbols) > 8:
        st.error("اختر 8 رموز أو أقل في كل عملية فحص.")
    elif not min_dte <= target_dte <= max_dte:
        st.error("يجب أن يكون DTE المستهدف داخل النطاق المحدد.")
    else:
        with st.spinner("يتم تحليل السوق والأصول وسلاسل الخيارات بالتتابع..."):
            candidates, diagnostics, market_context = scan_paper_universe(
                symbols,
                target_dte=target_dte,
                min_dte=min_dte,
                max_dte=max_dte,
                min_premium=min_premium,
                max_premium=max_premium,
                max_spread_pct=float(max_spread),
                min_volume=int(min_volume),
                min_open_interest=int(min_oi),
                risk_free_rate=rate_pct / 100,
                top_n_per_symbol=top_n,
            )
        st.session_state["falcon_universe_candidates"] = candidates
        st.session_state["falcon_universe_diagnostics"] = diagnostics
        st.session_state["falcon_universe_market"] = market_context
        st.session_state["falcon_universe_symbols"] = symbols

candidates = st.session_state.get("falcon_universe_candidates", pd.DataFrame())
diagnostics = st.session_state.get("falcon_universe_diagnostics", pd.DataFrame())
market_context = st.session_state.get("falcon_universe_market")

if market_context is not None:
    st.subheader("سياق السوق وقت الفحص")
    c1, c2, c3 = st.columns(3)
    c1.metric("حالة السوق الوصفية", market_context["regime"])
    c2.metric("ثقة التصنيف", market_context["confidence"])
    c3.metric("آخر تاريخ بيانات", market_context.get("latest_data_date") or "غير متاح")
    st.caption(market_context["data_note"])

if not diagnostics.empty:
    st.subheader("حالة فحص كل رمز")
    st.dataframe(diagnostics, use_container_width=True, hide_index=True)

if not candidates.empty:
    st.subheader("قائمة المرشحين الأعلى توافقاً مع معايير البحث")
    columns = [
        "symbol", "option_type", "contractSymbol", "expiry", "spot_reference",
        "mid", "strike", "daysToExpiry", "delta", "spread_pct_mid",
        "volume", "openInterest", "research_fit_score", "research_fit_label",
    ]
    labels = {
        "symbol": "الرمز الأساسي", "option_type": "النوع",
        "contractSymbol": "رمز العقد", "expiry": "الانتهاء",
        "spot_reference": "السعر المرجعي للأصل", "mid": "Mid تقريبي",
        "strike": "Strike", "daysToExpiry": "DTE",
        "delta": "Delta نموذجي", "spread_pct_mid": "السبريد %",
        "volume": "الحجم", "openInterest": "Open Interest",
        "research_fit_score": "درجة التوافق البحثي",
        "research_fit_label": "وصف التوافق",
    }
    st.dataframe(candidates[columns].rename(columns=labels), use_container_width=True, hide_index=True)
    with st.expander("تفاصيل أسباب ترتيب المرشحين"):
        st.dataframe(
            candidates[["symbol", "contractSymbol", "option_type", "research_fit_reasons"]].rename(columns={
                "symbol": "الرمز الأساسي", "contractSymbol": "رمز العقد",
                "option_type": "النوع", "research_fit_reasons": "تفاصيل المكونات",
            }),
            use_container_width=True,
            hide_index=True,
        )
    st.download_button(
        "تنزيل نتائج الفحص CSV",
        data=candidates.to_csv(index=False).encode("utf-8-sig"),
        file_name="falcon_paper_candidates.csv",
        mime="text/csv",
    )
elif not diagnostics.empty:
    st.info("لم تظهر مرشحات مطابقة. راجع حالة كل رمز وحدود البيانات؛ لا يتم اختراع عقود أو أسعار عند غياب المصدر.")

st.info(
    "هذه قائمة بحثية افتراضية فقط. درجة التوافق ليست احتمال نجاح أو ربح، ولا تمثل توصية شراء أو بيع. "
    "المصدر الحالي Yahoo Finance عبر yfinance وقد تكون الأسعار والسلسلة متأخرة أو ناقصة، "
    "والسعر المرجعي للأصل قد لا يتزامن مع لقطة سلسلة الخيارات. لا توجد أوامر أو صفقات فعلية."
)
