from __future__ import annotations

import pandas as pd
import streamlit as st

from falcon.market import load_history
from falcon.market_intelligence import build_market_intelligence
from falcon.multi_timeframe import load_multi_timeframe
from falcon.stock_analysis import analyze_stock_frame

st.set_page_config(page_title="Falcon — التحليل الفني المتقدم", page_icon="🦅", layout="wide")
st.title("🦅 Falcon — التحليل الفني المتقدم")
st.caption("تحليل وصفي متعدد الأطر الزمنية · بيانات تاريخية/قد تكون متأخرة · لا يصدر أوامر أو توصيات تنفيذية")

with st.sidebar:
    symbol = st.text_input("رمز السهم أو الصندوق", value="SPY").strip().upper()
    period = st.selectbox("الفترة", ["6mo", "1y", "2y", "5y"], index=1)
    interval = st.selectbox("الإطار الأساسي", ["1d", "1h", "1wk"], index=0)
    pivot_window = st.slider("نافذة تأكيد المحاور", 2, 8, 3)
    if st.button("تحديث البيانات", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if not symbol:
    st.info("أدخل رمزاً للمتابعة.")
    st.stop()

try:
    with st.spinner("تحميل بيانات السهم وتحليلها..."):
        history = load_history(symbol, period=period, interval=interval)
except Exception as exc:
    st.error(f"تعذر تحميل البيانات: {exc}")
    st.stop()

if history.empty:
    st.warning("لم تصل بيانات تاريخية لهذا الرمز؛ لن يتم إنشاء بيانات بديلة.")
    st.stop()

try:
    report = analyze_stock_frame(history, pivot_window)
except (ValueError, KeyError) as exc:
    st.error(f"تعذر بناء التحليل: {exc}")
    st.stop()

st.subheader(f"ملخص {symbol}")
st.metric("الحالة الفنية الوصفية", report["descriptive_state"])
st.caption(f"آخر شمعة: {report['as_of']} · عدد الشموع: {report['bars']} · {report['method_note']}")

a, b, c, d = st.columns(4)
a.metric("الإغلاق الأخير", f"{report['last_close']:,.2f}")
b.metric("RSI 14", f"{report['rsi14']:.1f}" if report["rsi14"] is not None else "—")
c.metric("ATR 14", f"{report['scenario_ranges']['atr']:.3f}" if report["scenario_ranges"]["atr"] is not None else "—")
d.metric("حجم / متوسط 20", f"{report['volume_ratio_20']:.2f}x" if report["volume_ratio_20"] is not None else "—")

st.subheader("اتجاه المتوسطات")
ema_rows = [
    {"المتوسط": "EMA 20", "القيمة": report["ema"]["ema20"]},
    {"المتوسط": "EMA 50", "القيمة": report["ema"]["ema50"]},
    {"المتوسط": "EMA 200", "القيمة": report["ema"]["ema200"]},
]
st.dataframe(pd.DataFrame(ema_rows), use_container_width=True, hide_index=True)

st.subheader("هيكل السوق")
structure = report["structure"]
st.write(f"**الهيكل:** {structure['trend']}")
st.write(f"**آخر حدث محتمل:** {structure['event']}")
st.caption(structure["note"])
p1, p2 = st.columns(2)
p1.metric("آخر قمة محورية مؤكدة", f"{structure['last_pivot_high']:.2f}" if structure["last_pivot_high"] is not None else "—")
p2.metric("آخر قاع محوري مؤكد", f"{structure['last_pivot_low']:.2f}" if structure["last_pivot_low"] is not None else "—")

st.subheader("مستويات Fibonacci المرجعية")
fib = report["fibonacci"]
if fib.get("levels"):
    st.caption(f"الساق المرجعية: {fib['direction']} · من {fib['swing_low']:.2f} إلى {fib['swing_high']:.2f}")
    f1, f2 = st.columns(2)
    with f1:
        st.markdown("**Retracement**")
        st.dataframe(pd.DataFrame([{"النسبة": k, "المستوى": round(v, 4)} for k, v in fib["levels"].items()]), use_container_width=True, hide_index=True)
    with f2:
        st.markdown("**Extensions**")
        st.dataframe(pd.DataFrame([{"النسبة": k, "المستوى": round(v, 4)} for k, v in fib.get("extensions", {}).items()]), use_container_width=True, hide_index=True)
else:
    st.info(fib["note"])

st.subheader("نطاقات الحساسية المبنية على ATR")
scenario = report["scenario_ranges"]
st.dataframe(pd.DataFrame([
    {"النطاق": "+1 ATR", "المستوى": scenario["upper_1atr"]},
    {"النطاق": "-1 ATR", "المستوى": scenario["lower_1atr"]},
    {"النطاق": "+2 ATR", "المستوى": scenario["upper_2atr"]},
    {"النطاق": "-2 ATR", "المستوى": scenario["lower_2atr"]},
]), use_container_width=True, hide_index=True)
st.caption(scenario["note"])

st.subheader("توافق الأطر الزمنية")
with st.spinner("مقارنة اليومي والساعة و4 ساعات المشتقة..."):
    mtf_rows, alignment = load_multi_timeframe(symbol)
st.metric("ملخص التوافق", alignment["label"])
st.caption(alignment["note"])
mtf_columns = ["timeframe", "trend", "momentum", "macd_state", "volume_state", "structure", "structure_event", "close", "rsi14", "bars", "source"]
st.dataframe(pd.DataFrame(mtf_rows)[mtf_columns], use_container_width=True, hide_index=True)

st.subheader("سياق السوق العام")
with st.spinner("قراءة المؤشرات والقطاعات..."):
    market = build_market_intelligence()
st.metric("حالة السوق العامة", market["regime"])
st.caption(f"ثقة التصنيف: {market['confidence']} · أحدث تاريخ بيانات: {market['latest_data_date'] or 'غير متاح'}")
st.dataframe(pd.DataFrame(market["indices"]), use_container_width=True, hide_index=True)
st.markdown("**القوة النسبية للقطاعات مقابل SPY**")
st.dataframe(pd.DataFrame(market["sectors"])[["symbol", "name", "change_20d_pct", "relative_20d_pct", "trend", "status"]], use_container_width=True, hide_index=True)
st.info("هذه الصفحة بحث وتحليل وصفي فقط. لا تنتج اختيار عقد أو توصية شراء أو بيع. بيانات Yahoo Finance تاريخية أو متأخرة وقد تكون ناقصة؛ تحقق من وقت آخر شمعة قبل تفسير النتائج.")
