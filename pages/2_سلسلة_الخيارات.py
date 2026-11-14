from __future__ import annotations

import streamlit as st
import pandas as pd
from falcon.auth import require_password
from falcon.options_data import load_option_chain, load_option_expirations

st.set_page_config(page_title="Falcon · سلسلة الخيارات", page_icon="🦅", layout="wide")
require_password()
st.title("سلسلة الخيارات — مختبر بيانات تعليمي")
st.caption("بيانات مزود خارجي قد تكون متأخرة أو ناقصة. هذه الصفحة للقراءة والمحاكاة فقط.")

with st.sidebar:
    symbol = st.text_input("رمز الأصل", value="SPY").strip().upper()
    st.caption("المصدر: Yahoo Finance عبر yfinance؛ لا توجد ضمانة لحداثة الأسعار أو اكتمال السلسلة.")

if not symbol:
    st.info("أدخل رمز أصل مدعوماً.")
    st.stop()

try:
    with st.spinner("جلب تواريخ الانتهاء المتاحة..."):
        expirations = load_option_expirations(symbol)
except Exception as exc:
    st.error(f"تعذر جلب تواريخ الخيارات لهذا الرمز: {exc}")
    st.stop()

if not expirations:
    st.warning("لم يُرجع المصدر تواريخ انتهاء لهذا الرمز. لم ننشئ بيانات بديلة.")
    st.stop()

expiration = st.selectbox("تاريخ الانتهاء المتاح لدى المصدر", expirations)
try:
    with st.spinner("تحميل سلسلة CALL وPUT..."):
        chain = load_option_chain(symbol, expiration)
except Exception as exc:
    st.error(f"تعذر تحميل السلسلة: {exc}")
    st.stop()

if chain.empty:
    st.warning("السلسلة فارغة لهذا التاريخ.")
    st.stop()

calls = chain[chain["side"] == "CALL"].copy()
puts = chain[chain["side"] == "PUT"].copy()
c1, c2, c3 = st.columns(3)
c1.metric("تاريخ الانتهاء", expiration)
c2.metric("عدد CALL", len(calls))
c3.metric("عدد PUT", len(puts))

st.info(
    "تنبيه جودة البيانات: يعرض الجدول الحقول التي أعادها المصدر فقط. "
    "لا يوفر هذا المصدر Greeks موثوقة ضمن هذه الواجهة؛ لذلك لا نحسب أو نختلق Delta أو Gamma أو Theta أو Vega. "
    "التذبذب الضمني والحجم والفائدة المفتوحة قد تكون فارغة أو متأخرة."
)

columns = ["contractSymbol", "strike", "lastPrice", "bid", "ask", "volume",
           "openInterest", "impliedVolatility", "inTheMoney"]
tab_call, tab_put, tab_all = st.tabs(["CALL", "PUT", "الكل"])
with tab_call:
    st.dataframe(calls[columns], use_container_width=True, hide_index=True)
with tab_put:
    st.dataframe(puts[columns], use_container_width=True, hide_index=True)
with tab_all:
    st.dataframe(chain[["side", *columns]], use_container_width=True, hide_index=True)

st.subheader("حقول لا يوفرها المصدر في هذه الواجهة")
st.dataframe(pd.DataFrame([
    {"الحقل": "Delta / Gamma", "الحالة": "غير متاح كقيمة مزود موثوقة"},
    {"الحقل": "Theta / Vega", "الحالة": "غير متاح كقيمة مزود موثوقة"},
    {"الحقل": "IV / OI / Volume", "الحالة": "تعرض فقط إذا أعادها المصدر؛ قد تكون فارغة أو متأخرة"},
    {"الحقل": "Bid / Ask spread", "الحالة": "يمكن اشتقاق الفرق حسابياً عندما يتوفر الطرفان، لكنه لا يثبت جودة التنفيذ"},
]), use_container_width=True, hide_index=True)
st.caption("لا تتضمن الصفحة ترتيب عقود أو إشارة دخول أو توجيهاً لشراء CALL أو PUT.")
