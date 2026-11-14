from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

from falcon.context import summarize_market_context
from falcon.indicators import add_indicators
from falcon.market import load_history
from falcon.scoring import describe_confluence

st.set_page_config(page_title="Falcon Swing Options", page_icon="🦅", layout="wide")
st.title("🦅 Falcon Swing Options")
st.caption("مساحة تعليمية لتحليل بنية السوق — Historical/delayed data only · Paper analysis")

with st.sidebar:
    st.header("إعداد التحليل")
    symbol = st.text_input("رمز السهم أو الصندوق", value="SPY").strip().upper()
    period = st.selectbox("الفترة التاريخية", ["6mo", "1y", "2y", "5y"], index=1)
    interval = st.selectbox("الإطار الزمني", ["1d", "1wk", "1h"], index=0)
    st.caption("مصدر البداية: Yahoo Finance عبر yfinance. قد تكون البيانات متأخرة أو غير متاحة لبعض الرموز.")

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
    st.warning("لا توجد بيانات متاحة لهذا الرمز والإطار الزمني. لم يتم إنشاء بيانات بديلة.")
    st.stop()

frame = add_indicators(raw)
context = summarize_market_context()
last = frame.iloc[-1]

m1, m2, m3, m4 = st.columns(4)
m1.metric("آخر إغلاق", f"{last['Close']:,.2f}")
m2.metric("EMA 20", f"{last['EMA20']:,.2f}" if last['EMA20'] == last['EMA20'] else "—")
m3.metric("RSI 14", f"{last['RSI14']:.1f}" if last['RSI14'] == last['RSI14'] else "—")
m4.metric("ATR 14", f"{last['ATR14']:.2f}" if last['ATR14'] == last['ATR14'] else "—")

st.subheader("السياق العام للسوق")
st.write(context["message"])
st.caption(context["data_note"])

st.subheader(f"{symbol} — السعر والمؤشرات")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=frame.index, open=frame["Open"], high=frame["High"], low=frame["Low"], close=frame["Close"], name=symbol))
fig.add_trace(go.Scatter(x=frame.index, y=frame["EMA20"], name="EMA 20", line={"width": 1.4}))
fig.add_trace(go.Scatter(x=frame.index, y=frame["EMA50"], name="EMA 50", line={"width": 1.4}))
fig.add_trace(go.Scatter(x=frame.index, y=frame["EMA200"], name="EMA 200", line={"width": 1.4}))
fig.update_layout(height=560, xaxis_rangeslider_visible=False, margin={"l": 10, "r": 10, "t": 25, "b": 10})
st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("قراءة وصفية للاتجاه")
    st.write(describe_confluence(frame))
    st.caption("القراءة وصفية للعوامل الظاهرة وليست احتمال نجاح أو إشارة شراء/بيع.")
with right:
    st.subheader("RSI و MACD")
    osc = go.Figure()
    osc.add_trace(go.Scatter(x=frame.index, y=frame["RSI14"], name="RSI 14"))
    osc.add_hline(y=70, line_dash="dot")
    osc.add_hline(y=30, line_dash="dot")
    osc.update_layout(height=250, yaxis_range=[0, 100], margin={"l": 10, "r": 10, "t": 20, "b": 10})
    st.plotly_chart(osc, use_container_width=True)
    macd_fig = go.Figure()
    macd_fig.add_trace(go.Scatter(x=frame.index, y=frame["MACD"], name="MACD"))
    macd_fig.add_trace(go.Scatter(x=frame.index, y=frame["MACDSignal"], name="Signal"))
    macd_fig.update_layout(height=250, margin={"l": 10, "r": 10, "t": 20, "b": 10})
    st.plotly_chart(macd_fig, use_container_width=True)

with st.expander("عرض آخر السجلات"):
    st.dataframe(frame.tail(20), use_container_width=True)

st.warning("تنبيه تعليمي: هذه النسخة لا تحلل سلسلة الخيارات أو Greeks، ولا تنتج عقود CALL/PUT. سنضيف موصل بيانات موثقاً بعد تحديد مزود مناسب، مع إظهار حداثة البيانات وتغطيتها بوضوح.")
