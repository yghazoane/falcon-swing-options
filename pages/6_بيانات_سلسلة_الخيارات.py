from __future__ import annotations

import pandas as pd
import streamlit as st

from falcon.auth import require_password
from falcon.market import load_history
from falcon.options_data import get_option_expirations, load_options_chain

st.set_page_config(page_title="Falcon · بيانات سلسلة الخيارات", page_icon="🦅", layout="wide")
require_password()
st.title("بيانات سلسلة الخيارات")
st.caption("عرض بحثي للبيانات التي يعيدها مزود خارجي؛ لا يمثل أسعاراً مضمونة التنفيذ ولا يصدر توصيات.")

with st.sidebar:
    symbol = st.text_input("رمز الأصل", value="SPY").strip().upper()
    rate_pct = st.number_input("معدل الفائدة المفترض لحساب Greeks %", min_value=-5.0, max_value=30.0, value=4.0, step=0.25)
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
    "Bid/Ask وVolume وOpen Interest قد تكون متأخرة أو ناقصة؛ تحقق من مزود مرخص قبل الاعتماد عليها."
)
st.caption(
    f"وقت الاسترجاع UTC: {snapshot['retrieved_at_utc']} · "
    f"الانتهاء: {snapshot['expiry']} · DTE التقريبي: {snapshot['days_to_expiry']} · "
    f"المصدر: {snapshot['provider']}"
)

columns = [
    "contractSymbol", "strike", "lastPrice", "bid", "ask", "mid",
    "spread_pct_mid", "volume", "openInterest", "impliedVolatility",
    "delta", "gamma", "theta_per_day", "vega_per_1pct",
]
labels = {
    "contractSymbol": "رمز العقد", "strike": "Strike", "lastPrice": "آخر سعر",
    "bid": "Bid", "ask": "Ask", "mid": "Mid تقريبي",
    "spread_pct_mid": "السبريد % من Mid", "volume": "الحجم",
    "openInterest": "Open Interest", "impliedVolatility": "IV",
    "delta": "Delta نموذجي", "gamma": "Gamma نموذجي",
    "theta_per_day": "Theta/يوم", "vega_per_1pct": "Vega/1% IV",
}

for key, title in (("calls", "CALL — بيانات المصدر"), ("puts", "PUT — بيانات المصدر")):
    st.subheader(title)
    frame = snapshot[key].copy()
    if frame.empty:
        st.info("لا توجد صفوف أعادها المصدر لهذا النوع.")
        continue
    st.dataframe(frame[columns].rename(columns=labels), use_container_width=True, hide_index=True)
    st.caption(
        "Greeks والقيمة النظرية محسوبة محلياً بنموذج Black–Scholes باستخدام السعر المرجعي وIV المعاد من المصدر؛ "
        "ليست Greeks منشورة من البورصة، ولا تأخذ توزيعات الأرباح أو خصائص التسوية والتمرين المبكر في الحسبان."
    )

st.info(
    "هذه الصفحة تعرض سلسلة بحثية للمقارنة والتحقق من جودة البيانات فقط. "
    "لا ترتب العقود بغرض الشراء، ولا تحدد عقداً أو نقطة دخول أو أمر تنفيذ."
)
