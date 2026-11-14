from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
from falcon.context import summarize_market_context
from falcon.fibonacci import latest_fibonacci_levels
from falcon.indicators import add_indicators
from falcon.market import load_history
from falcon.scoring import describe_confluence
from falcon.structure import describe_market_structure

st.set_page_config(page_title="Falcon Swing Options", page_icon="🦅", layout="wide")
st.title("🦅 Falcon Swing Options")
st.caption("مساحة تعليمية لتحليل بنية السوق — Historical/delayed data only · Paper analysis")
with st.sidebar:
    st.header("إعداد التحليل")
    symbol = st.text_input("رمز السهم أو الصندوق", value="SPY").strip().upper()
    period = st.selectbox("الفترة التاريخية", ["6mo", "1y", "2y", "5y"], index=1)
    interval = st.selectbox("الإطار الزمني", ["1d", "1wk", "1h"], index=0)
    pivot_window = st.slider("حساسية المحاور (شموع)", 2, 8, 3)
    st.caption("المصدر: Yahoo Finance عبر yfinance؛ لا يضمن بيانات لحظية.")
if not symbol:
    st.info("أدخل رمزاً لعرض البيانات التاريخية.")
    st.stop()
with st.spinner("جاري تحميل البيانات التاريخية..."):
    try:
        raw = load_history(symbol, period=period, interval=interval)
    except Exception as exc:
        st.error(f"تعذر تحميل البيانات: {exc}")
        st.stop()
if raw.empty:
    st.warning("لا توجد بيانات متاحة لهذا الرمز. لم يتم إنشاء بيانات بديلة.")
    st.stop()
frame = add_indicators(raw)
structure = describe_market_structure(frame, pivot_window)
fib = latest_fibonacci_levels(frame, pivot_window)
context = summarize_market_context()
last = frame.iloc[-1]
m1, m2, m3, m4 = st.columns(4)
m1.metric("آخر إغلاق", f"{last['Close']:,.2f}")
m2.metric("EMA 20", f"{last['EMA20']:,.2f}" if last["EMA20"] == last["EMA20"] else "—")
m3.metric("RSI 14", f"{last['RSI14']:.1f}" if last["RSI14"] == last["RSI14"] else "—")
m4.metric("ATR 14", f"{last['ATR14']:.2f}" if last["ATR14"] == last["ATR14"] else "—")
st.subheader("السياق العام للسوق")
st.write(context["message"])
st.caption(context["data_note"])
st.subheader(f"{symbol} — السعر والمؤشرات")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=frame.index, open=frame["Open"], high=frame["High"], low=frame["Low"], close=frame["Close"], name=symbol))
for col, label in (("EMA20", "EMA 20"), ("EMA50", "EMA 50"), ("EMA200", "EMA 200")):
    fig.add_trace(go.Scatter(x=frame.index, y=frame[col], name=label, line={"width": 1.4}))
fig.add_trace(go.Scatter(x=structure["annotated"].index, y=structure["annotated"]["PivotHigh"], mode="markers", name="Swing High", marker={"symbol": "triangle-down", "size": 9}))
fig.add_trace(go.Scatter(x=structure["annotated"].index, y=structure["annotated"]["PivotLow"], mode="markers", name="Swing Low", marker={"symbol": "triangle-up", "size": 9}))
fig.update_layout(height=560, xaxis_rangeslider_visible=False, margin={"l": 10, "r": 10, "t": 25, "b": 10})
st.plotly_chart(fig, use_container_width=True)
left, right = st.columns(2)
with left:
    st.subheader("قراءة وصفية للاتجاه")
    st.write(describe_confluence(frame))
    st.subheader("هيكل السوق")
    st.write(f"الحالة البنيوية: {structure['trend']}")
    st.write(structure["event"])
    st.caption(structure["note"])
with right:
    st.subheader("RSI و MACD")
    osc = go.Figure()
    osc.add_trace(go.Scatter(x=frame.index, y=frame["RSI14"], name="RSI 14"))
    osc.add_hline(y=70, line_dash="dot")
    osc.add_hline(y=30, line_dash="dot")
    osc.update_layout(height=250, yaxis_range=[0, 100], margin={"l": 10, "r": 10, "t": 20, "b": 10})
    st.plotly_chart(osc, use_container_width=True)
    macd = go.Figure()
    macd.add_trace(go.Scatter(x=frame.index, y=frame["MACD"], name="MACD"))
    macd.add_trace(go.Scatter(x=frame.index, y=frame["MACDSignal"], name="Signal"))
    macd.update_layout(height=250, margin={"l": 10, "r": 10, "t": 20, "b": 10})
    st.plotly_chart(macd, use_container_width=True)
st.subheader("مستويات Fibonacci المرجعية")
if fib["levels"]:
    st.caption(f"اتجاه الساق: {fib['direction']} · النطاق: {fib['swing_low']:.2f} — {fib['swing_high']:.2f}")
    st.dataframe([{"النسبة": k, "المستوى": round(v, 4)} for k, v in fib["levels"].items()], use_container_width=True, hide_index=True)
else:
    st.info(fib["note"])
st.caption(fib["note"])
with st.expander("عرض آخر السجلات"):
    st.dataframe(frame.tail(20), use_container_width=True)
st.warning("نسخة تعليمية فقط: لا تحلل سلسلة الخيارات أو Greeks، ولا تنتج عقود CALL/PUT. ستضاف بيانات الخيارات بعد تحديد مزود موثق وحدود تغطيته.")
