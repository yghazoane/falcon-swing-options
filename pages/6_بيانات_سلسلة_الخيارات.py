from __future__ import annotations

import pandas as pd
import streamlit as st

from falcon.auth import require_password
from falcon.market import load_history
from falcon.options_data import get_option_expirations, load_options_chain
from falcon.contract_screening import rank_contract_data_quality
from falcon.market_intelligence import build_market_intelligence
from falcon.multi_timeframe import load_multi_timeframe

st.set_page_config(page_title="Falcon · بيانات سلسلة الخيارات", page_icon="🦅", layout="wide")
require_password()
st.title("محرك فرز جودة بيانات سلسلة الخيارات")
st.caption("فرز بحثي افتراضي لخصائص البيانات والسيولة المنشورة؛ لا يقيّم اتجاه العقد ولا يصدر توصية شراء أو تنفيذ.")

with st.sidebar:
    symbol = st.text_input("رمز الأصل", value="SPY").strip().upper()
    rate_pct = st.number_input("معدل الفائدة المفترض لحساب Greeks %", min_value=-5.0, max_value=30.0, value=4.0, step=0.25)
    st.subheader("مرشحات البحث الافتراضي")
    min_premium, max_premium = st.slider("نطاق السعر الوسطي بالدولار", 0.0, 20.0, (0.0, 4.0), 0.1)
    max_spread = st.slider("أقصى سبريد % من السعر الوسطي", 1, 100, 20)
    min_volume = st.number_input("أقل حجم تداول منشور", min_value=0, value=10, step=10)
    min_oi = st.number_input("أقل Open Interest منشور", min_value=0, value=100, step=50)
    min_dte, max_dte = st.slider("نطاق الأيام حتى الانتهاء", 0, 180, (7, 60))
    refresh = st.button("تحديث سلسلة الخيارات", use_container_width=True)

if not symbol:
    st.info("أدخل رمز الأصل.")
    st.stop()

try:
    with st.spinner("جلب تواريخ الانتهاء المتاحة..."):
        expirations = get_option_expirations(symbol)
except Exception as exc:
    st.error(f"تعذر جلب تواريخ الانتهاء: {exc}")
    st.stop()

if not expirations:
    st.warning("لم يوفّر المصدر تواريخ انتهاء لهذا الرمز. لا يتم إنشاء بيانات بديلة.")
    st.stop()

expiry = st.selectbox("تاريخ الانتهاء", expirations)
try:
    history = load_history(symbol, period="5d", interval="1d")
except Exception as exc:
    st.error(f"تعذر جلب السعر المرجعي للأصل: {exc}")
    st.stop()

if history.empty or "Close" not in history:
    st.warning("لا يتوفر سعر مرجعي من المصدر؛ لا يمكن حساب Greeks.")
    st.stop()

spot = float(history["Close"].dropna().iloc[-1])
price_time = history["Close"].dropna().index[-1]
st.metric("السعر المرجعي التاريخي/المتاح", f"{spot:,.2f}")
st.caption(f"تاريخ السعر المرجعي: {price_time}. قد لا يكون لحظياً.")

try:
    with st.spinner("تحميل سلسلة العقود وحساب المقاييس النظرية..."):
        snapshot = load_options_chain(symbol, expiry, spot, rate_pct / 100)
except Exception as exc:
    st.error(f"تعذر تحميل سلسلة الخيارات: {exc}")
    st.stop()

st.warning(
    "مصدر البيانات: Yahoo Finance عبر yfinance. وقت الاسترجاع أدناه هو وقت جلب البيانات وليس وقت آخر تحديث من البورصة. "
    "Bid/Ask وVolume وOpen Interest قد تكون متأخرة أو ناقصة؛ لا تعتبرها أسعاراً مضمونة التنفيذ."
)
st.caption(
    f"وقت الاسترجاع UTC: {snapshot['retrieved_at_utc']} · "
    f"الانتهاء: {snapshot['expiry']} · DTE التقريبي: {snapshot['days_to_expiry']:.2f} · "
    f"المصدر: {snapshot['provider']}"
)
st.caption(snapshot["spot_reference_warning"])
st.caption(snapshot["model_assumptions"])

st.subheader("سياق السوق والأصل الأساسي")
try:
    with st.spinner("قراءة اتجاه المؤشرات والأطر الزمنية..."):
        market_context = build_market_intelligence()
        timeframe_rows, timeframe_alignment = load_multi_timeframe(symbol)
    context_cols = st.columns(3)
    context_cols[0].metric("حالة السوق العامة", market_context["regime"])
    context_cols[1].metric("درجة ثقة التصنيف", market_context["confidence"])
    context_cols[2].metric("توافق أطر الأصل", timeframe_alignment["label"])
    if market_context.get("selected_benchmarks"):
        st.dataframe(pd.DataFrame(market_context["selected_benchmarks"]), use_container_width=True, hide_index=True)
    timeframe_frame = pd.DataFrame(timeframe_rows)
    if not timeframe_frame.empty:
        st.dataframe(
            timeframe_frame[["timeframe", "trend", "momentum", "macd_state", "volume_state", "status", "source"]]
            .rename(columns={
                "timeframe": "الإطار", "trend": "الاتجاه",
                "momentum": "الزخم", "macd_state": "MACD",
                "volume_state": "الحجم", "status": "حالة البيانات",
                "source": "المصدر",
            }),
            use_container_width=True,
            hide_index=True,
        )
    st.caption(market_context["method_note"])
except Exception as exc:
    st.warning(f"تعذر تحميل بعض عناصر سياق السوق: {type(exc).__name__}")

columns = [
    "contractSymbol", "strike", "lastPrice", "bid", "ask", "mid",
    "spread_pct_mid", "volume", "openInterest", "impliedVolatility",
    "daysToExpiry", "delta", "gamma", "theta_per_day", "vega_per_1pct",
    "data_quality_score", "screen_status",
]
labels = {
    "contractSymbol": "رمز العقد", "strike": "Strike", "lastPrice": "آخر سعر",
    "bid": "Bid", "ask": "Ask", "mid": "Mid تقريبي",
    "spread_pct_mid": "السبريد % من Mid", "volume": "الحجم",
    "openInterest": "Open Interest", "impliedVolatility": "IV",
    "daysToExpiry": "DTE", "delta": "Delta نموذجي",
    "gamma": "Gamma نموذجي", "theta_per_day": "Theta/يوم",
    "vega_per_1pct": "Vega/1% IV", "data_quality_score": "درجة جودة البيانات",
    "screen_status": "نتيجة المرشحات",
}

screened = {}
for key, title in (("calls", "CALL — فرز جودة البيانات"), ("puts", "PUT — فرز جودة البيانات")):
    frame = rank_contract_data_quality(
        snapshot[key],
        min_premium=min_premium,
        max_premium=max_premium,
        max_spread_pct=float(max_spread),
        min_volume=int(min_volume),
        min_open_interest=int(min_oi),
        min_days_to_expiry=float(min_dte),
        max_days_to_expiry=float(max_dte),
    )
    screened[key] = frame
    st.subheader(title)
    if frame.empty:
        st.info("لا توجد صفوف أعادها المصدر لهذا النوع.")
        continue
    matched = int(frame["screen_status"].eq("مطابق لمرشحات جودة البيانات").sum())
    st.metric("عدد الصفوف المطابقة لمرشحات جودة البيانات", matched)
    st.dataframe(frame[columns].rename(columns=labels), use_container_width=True, hide_index=True)
    with st.expander("أسباب التقييم لكل صف"):
        st.dataframe(
            frame[["contractSymbol", "data_quality_score", "screen_reasons"]].rename(columns={
                "contractSymbol": "رمز العقد",
                "data_quality_score": "درجة جودة البيانات",
                "screen_reasons": "تفاصيل تحقق المرشحات",
            }),
            use_container_width=True,
            hide_index=True,
        )
    st.caption(
        "Greeks والقيمة النظرية محسوبة محلياً بنموذج Black–Scholes باستخدام السعر المرجعي وIV المعاد من المصدر؛ "
        "ليست Greeks منشورة من البورصة، ولا تأخذ توزيعات الأرباح أو خصائص التسوية والتمرين المبكر في الحسبان."
    )

st.info(
    "درجة جودة البيانات تقيس اكتمال العرض والسبريد والحجم وOpen Interest وIV وDTE والسعر الوسطي وفق الحدود التي تختارها. "
    "لا تقيس اتجاه السوق أو احتمالية الربح أو ملاءمة العقد للشراء؛ النتائج قائمة مراقبة افتراضية للبحث والمحاكاة فقط."
)
