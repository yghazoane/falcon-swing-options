from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from falcon.auth import require_password
from falcon.context import summarize_market_context
from falcon.fibonacci import latest_fibonacci_levels
from falcon.indicators import add_indicators
from falcon.market import load_history
from falcon.regime import market_dashboard, compare_timeframes
from falcon.scoring import describe_confluence
from falcon.structure import describe_market_structure

st.set_page_config(page_title="Falcon Swing Options", page_icon="🦅", layout="wide")
require_password()
st.title("🦅 Falcon Swing Options")
st.caption("مساحة تعليمية لتحليل بنية السوق — بيانات تاريخية/قد تكون متأخرة · محاكاة فقط")
with st.sidebar:
    st.header("إعداد التحليل")
    symbol = st.text_input("رمز السهم أو الصندوق", value="SPY").strip().upper()
    period = st.selectbox("الفترة التاريخية", ["6mo", "1y", "2y", "5y"], index=1)
    interval = st.selectbox("الإطار الأساسي", ["1d", "1wk", "1h"], index=0)
    pivot_window = st.slider("حساسية المحاور (شموع)", 2, 8, 3)
    st.caption("المصدر الحالي: Yahoo Finance عبر yfinance. لا توجد ضمانة للتوقيت الفوري أو اكتمال التغطية.")

if not symbol:
    st.info("أدخل رمزاً لعرض البيانات التاريخية.")
    st.stop()
try:
    with st.spinner("تحميل بيانات الرمز..."):
        raw = load_history(symbol, period=period, interval=interval)
except Exception as exc:
    st.error(f"تعذر تحميل البيانات: {exc}")
    st.stop()
if raw.empty:
    st.warning("لا توجد بيانات متاحة لهذا الرمز. لم يتم توليد بيانات بديلة.")
    st.stop()

frame = add_indicators(raw)
structure = describe_market_structure(frame, pivot_window)
fib = latest_fibonacci_levels(frame, pivot_window)
last = frame.iloc[-1]

tab_market, tab_asset, tab_options, tab_method = st.tabs(["السوق العام", "تحليل الرمز", "مفاهيم الخيارات", "المنهجية والبيانات"])
with tab_market:
    st.subheader("مؤشرات السوق الرئيسية")
    with st.spinner("قراءة المؤشرات والقطاعات والمتغيرات الكلية..."):
        dash = market_dashboard()
    def show_table(items, title):
        st.markdown(f"**{title}**")
        df = pd.DataFrame(items)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
    show_table(dash["indices"], "المؤشرات وصناديق المتابعة")
    show_table(dash["sectors"], "صناديق القطاعات")
    show_table(dash["macro"], "متغيرات كلية بديلة")
    st.info("هذه الرموز بدائل متابعة وليست قياسات مباشرة لكل مؤشر اقتصادي. لا توجد في هذه النسخة تغذية أخبار فدرالية أو تقويم اقتصادي آلي؛ لذلك لا نعرض عناوين أو أحداثاً غير موثقة.")
    st.subheader("توافق الأطر الزمنية")
    with st.spinner("مقارنة اليومي والساعة و4 ساعات المشتقة..."):
        mtf = compare_timeframes(symbol)
    st.dataframe(pd.DataFrame(mtf), use_container_width=True, hide_index=True)
    st.caption("إطار 4 ساعات مشتق بتجميع شموع الساعة، وقد تختلف حدوده عن جلسات السوق ومصدر بيانات أصلي 4H.")
with tab_asset:
    st.subheader(f"{symbol} — السعر والمؤشرات")
    a, b, c, d = st.columns(4)
    a.metric("آخر إغلاق", f"{last['Close']:,.2f}")
    b.metric("EMA 20", f"{last['EMA20']:,.2f}" if pd.notna(last["EMA20"]) else "—")
    c.metric("RSI 14", f"{last['RSI14']:.1f}" if pd.notna(last["RSI14"]) else "—")
    d.metric("ATR 14", f"{last['ATR14']:.2f}" if pd.notna(last["ATR14"]) else "—")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=frame.index, open=frame["Open"], high=frame["High"], low=frame["Low"], close=frame["Close"], name=symbol))
    for col, label in (("EMA20", "EMA 20"), ("EMA50", "EMA 50"), ("EMA200", "EMA 200")):
        fig.add_trace(go.Scatter(x=frame.index, y=frame[col], name=label, line={"width": 1.4}))
    fig.add_trace(go.Scatter(x=structure["annotated"].index, y=structure["annotated"]["PivotHigh"], mode="markers", name="Swing High", marker={"symbol": "triangle-down", "size": 9}))
    fig.add_trace(go.Scatter(x=structure["annotated"].index, y=structure["annotated"]["PivotLow"], mode="markers", name="Swing Low", marker={"symbol": "triangle-up", "size": 9}))
    fig.update_layout(height=540, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**القراءة الفنية الوصفية**")
        st.write(describe_confluence(frame))
        st.markdown("**هيكل السوق**")
        st.write(f"{structure['trend']} — {structure['event']}")
        st.caption(structure["note"])
    with col2:
        osc = go.Figure()
        osc.add_trace(go.Scatter(x=frame.index, y=frame["RSI14"], name="RSI 14"))
        osc.add_hline(y=70, line_dash="dot")
        osc.add_hline(y=30, line_dash="dot")
        osc.update_layout(height=230, yaxis_range=[0, 100])
        st.plotly_chart(osc, use_container_width=True)
        macd = go.Figure()
        macd.add_trace(go.Scatter(x=frame.index, y=frame["MACD"], name="MACD"))
        macd.add_trace(go.Scatter(x=frame.index, y=frame["MACDSignal"], name="Signal"))
        macd.update_layout(height=230)
        st.plotly_chart(macd, use_container_width=True)
    st.subheader("مستويات Fibonacci المرجعية")
    if fib["levels"]:
        st.caption(f"اتجاه الساق: {fib['direction']} · النطاق: {fib['swing_low']:.2f} — {fib['swing_high']:.2f}")
        st.dataframe([{"النسبة": k, "المستوى": round(v, 4)} for k, v in fib["levels"].items()], use_container_width=True, hide_index=True)
    else:
        st.info(fib["note"])
    with st.expander("آخر السجلات"):
        st.dataframe(frame.tail(25), use_container_width=True)
with tab_options:
    st.subheader("مختبر مفاهيم الخيارات")
    st.write("هذه الصفحة تشرح حقول سلسلة الخيارات التي ستُعرض عند ربط مزود بيانات مرخص، دون اختيار عقد أو توجيه قرار تداول.")
    st.dataframe(pd.DataFrame([
        {"الحقل": "Strike", "المعنى": "سعر التنفيذ"},
        {"الحقل": "Expiry / DTE", "المعنى": "تاريخ الانتهاء وعدد الأيام المتبقية"},
        {"الحقل": "Delta / Gamma", "المعنى": "حساسية السعر ومعدل تغير دلتا"},
        {"الحقل": "Theta / Vega", "المعنى": "حساسية الوقت والتذبذب الضمني"},
        {"الحقل": "IV", "المعنى": "التذبذب الضمني"},
        {"الحقل": "Open Interest / Volume", "المعنى": "العقود المفتوحة وحجم التداول"},
        {"الحقل": "Bid / Ask / Spread", "المعنى": "أسعار العرض والطلب واتساع الفارق"},
    ]), use_container_width=True, hide_index=True)
    st.warning("لا توجد حالياً سلسلة خيارات موثوقة أو Greeks مباشرة ضمن مصدر yfinance المستخدم هنا. لن نملأ هذه الحقول بقيم افتراضية.")
with tab_method:
    st.subheader("مصادر البيانات وحدودها")
    st.markdown("- الأسعار: Yahoo Finance عبر yfinance، تاريخية وقد تكون متأخرة أو ناقصة.\n- 4H: مشتقة من شموع الساعة.\n- أخبار الفيدرالي والتقويم الاقتصادي: غير موصولة حالياً.\n- بيانات الخيارات وGreeks: تتطلب مزوداً منفصلاً واتفاقية استخدام مناسبة.\n- لا يوجد تنفيذ أوامر أو ربط وسيط.")
    st.subheader("كيف تُقرأ النتائج؟")
    st.write("المخرجات تصف توافق مؤشرات تاريخية فقط، وليست احتمال نجاح أو توصية أو تنبؤاً مضموناً. قد تتغير النتائج عند تحديث البيانات.")
st.caption("Falcon Swing Options · Educational research workspace · Paper analysis only")
