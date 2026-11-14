from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from falcon.auth import require_password
from falcon.market_intelligence import build_market_intelligence
from falcon.technical_analysis import analyze_stock_technicals
from falcon.indicators import add_indicators
from falcon.market import load_history
from falcon.multi_timeframe import load_multi_timeframe
from falcon.options_lab import black_scholes, expiration_value
from falcon.scoring import describe_confluence
from falcon.structure import describe_market_structure

st.set_page_config(page_title="Falcon · مختبر الخيارات والمحاكاة", page_icon="🦅", layout="wide")
require_password()
st.title("مختبر الخيارات والمحاكاة")
st.caption("تحليل مترابط للسهم والسوق + نموذج تسعير افتراضي. لا توجد سلسلة عقود حية أو توصيات أو تنفيذ صفقات.")

with st.sidebar:
    st.header("بيانات الأصل")
    symbol = st.text_input("رمز السهم أو الصندوق", value="SPY").strip().upper()
    period = st.selectbox("الفترة التاريخية", ["6mo", "1y", "2y", "5y"], index=1)
    st.caption("مصدر السعر: Yahoo Finance عبر yfinance؛ تاريخي أو متأخر وغير مضمون اللحظية.")

if not symbol:
    st.info("أدخل رمزاً لبدء التحليل.")
    st.stop()

try:
    with st.spinner(f"تحميل بيانات {symbol} والسياق العام..."):
        raw = load_history(symbol, period=period, interval="1d")
        market_intelligence = build_market_intelligence()
        timeframe_rows, timeframe_alignment = load_multi_timeframe(symbol)
except Exception as exc:
    st.error(f"تعذر تحميل البيانات: {exc}")
    st.stop()

if raw.empty:
    st.warning("لا توجد بيانات تاريخية متاحة لهذا الرمز. لم يتم إنشاء أسعار بديلة.")
    st.stop()

frame = add_indicators(raw)
last = frame.iloc[-1]
structure = describe_market_structure(frame)
technical = analyze_stock_technicals(frame)
spot = float(last["Close"])
last_time = frame.index[-1]

st.subheader("1) قراءة السوق العام")
market_cols = st.columns(3)
market_cols[0].metric("حالة السوق", market_intelligence["regime"])
market_cols[1].metric("ثقة التصنيف", market_intelligence["confidence"])
market_cols[2].metric("آخر تاريخ بيانات", market_intelligence["latest_data_date"] or "غير متاح")
st.caption(market_intelligence["method_note"])
st.caption(market_intelligence["data_note"])
st.subheader(f"2) قراءة السهم: {symbol}")
tech_cols = st.columns(4)
tech_cols[0].metric("اتجاه المتوسطات", technical["trend"])
tech_cols[1].metric("الزخم", technical["momentum"])
tech_cols[2].metric("الحجم", technical["volume"])
tech_cols[3].metric("ATR %", f"{technical['atr_pct']:.2f}%" if technical["atr_pct"] is not None else "—")
st.caption(technical["structure"]["event"] + " · " + technical["note"])
technical_levels = [
    {"العنصر": "آخر قاع محوري مؤكد", "القيمة": technical["support"]},
    {"العنصر": "آخر قمة محورية مؤكدة", "القيمة": technical["resistance"]},
    {"العنصر": "POC تقريبي للحجم حسب السعر", "القيمة": technical["volume_profile_poc"]},
    {"العنصر": "نسبة الحجم إلى متوسط 20 شمعة", "القيمة": technical["volume_ratio"]},
]
st.dataframe(pd.DataFrame(technical_levels), use_container_width=True, hide_index=True)
st.caption(f"آخر إغلاق متاح: {last_time} · السعر المرجعي للنموذج: {spot:,.2f}")
cols = st.columns(4)
cols[0].metric("آخر إغلاق", f"{spot:,.2f}")
cols[1].metric("RSI 14", f"{last['RSI14']:.1f}" if pd.notna(last["RSI14"]) else "—")
cols[2].metric("ATR 14", f"{last['ATR14']:.2f}" if pd.notna(last["ATR14"]) else "—")
cols[3].metric("EMA 20", f"{last['EMA20']:.2f}" if pd.notna(last["EMA20"]) else "—")
left, right = st.columns(2)
with left:
    st.markdown("**التوافق الفني الوصفي**")
    st.write(describe_confluence(frame))
    st.markdown("**هيكل السوق**")
    st.write(f"{structure['trend']} — {structure['event']}")
    st.caption(structure["note"])
    st.markdown("**توافق الأطر الزمنية للسهم**")
    st.metric("ملخص الأطر", timeframe_alignment["label"])
    st.caption(timeframe_alignment["note"])
    timeframe_table = pd.DataFrame(timeframe_rows)[[
        "timeframe", "trend", "momentum", "macd_state", "volume_state",
        "structure", "rsi14", "bars", "source"
    ]].rename(columns={
        "timeframe": "الإطار", "trend": "الاتجاه", "momentum": "الزخم",
        "macd_state": "MACD", "volume_state": "الحجم", "structure": "هيكل السوق",
        "rsi14": "RSI 14", "bars": "عدد الشموع", "source": "مصدر البيانات"
    })
    st.dataframe(timeframe_table, use_container_width=True, hide_index=True)
with right:
    st.markdown("**المتوسطات المتحركة**")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=frame.index, y=frame["Close"], name="Close"))
    for col in ("EMA20", "EMA50", "EMA200"):
        fig.add_trace(go.Scatter(x=frame.index, y=frame[col], name=col))
    fig.update_layout(height=340, margin={"l": 10, "r": 10, "t": 20, "b": 10})
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("3) افتراضات عقد تجريبي")
st.warning(
    "أدخل افتراضات تعليمية بنفسك. هذه الصفحة لا تجلب عقوداً فعلية ولا تقترح Strike أو تاريخ انتهاء، "
    "ولا تعرض سعراً قابلاً للتنفيذ. النموذج أوروبي مبسط ولا يمثل تسعير السوق أو شروط كل عقد."
)
with st.form("option_model_inputs"):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        option_type_label = st.selectbox("نوع المثال", ["Call", "Put"])
        option_type = "call" if option_type_label == "Call" else "put"
    with c2:
        strike = st.number_input("Strike افتراضي", min_value=0.01, value=round(spot, 2), step=0.5)
    with c3:
        dte = st.number_input("الأيام حتى الانتهاء (DTE)", min_value=0, max_value=3650, value=30, step=1)
    with c4:
        iv_pct = st.number_input("التقلب المفترض IV %", min_value=1.0, max_value=500.0, value=30.0, step=1.0)
    c5, c6 = st.columns(2)
    with c5:
        rate_pct = st.number_input("معدل خالٍ من المخاطر مفترض %", min_value=-5.0, max_value=30.0, value=4.0, step=0.25)
    with c6:
        multiplier = st.number_input("مضاعف العقد لأغراض العرض", min_value=1, max_value=10000, value=100, step=1)
    submitted = st.form_submit_button("احسب النموذج الافتراضي", type="primary")

if "falcon_option_model" not in st.session_state:
    st.session_state["falcon_option_model"] = {
        "option_type": "call", "strike": round(spot, 2), "dte": 30,
        "iv_pct": 30.0, "rate_pct": 4.0, "multiplier": 100,
    }
if submitted:
    st.session_state["falcon_option_model"] = {
        "option_type": option_type, "strike": float(strike), "dte": int(dte),
        "iv_pct": float(iv_pct), "rate_pct": float(rate_pct), "multiplier": int(multiplier),
    }

params = st.session_state["falcon_option_model"]
try:
    model = black_scholes(
        spot=spot, strike=params["strike"], days_to_expiry=params["dte"],
        volatility=params["iv_pct"] / 100, risk_free_rate=params["rate_pct"] / 100,
        option_type=params["option_type"],
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

st.markdown("**القيمة النظرية ومقاييس الحساسية — لكل وحدة من الأصل**")
g = st.columns(5)
g[0].metric("قيمة نظرية", f"{model['price']:.4f}")
g[1].metric("Delta", f"{model['delta']:.4f}")
g[2].metric("Gamma", f"{model['gamma']:.5f}")
g[3].metric("Theta / يوم", f"{model['theta_per_day']:.5f}")
g[4].metric("Vega / 1% IV", f"{model['vega_per_1pct']:.5f}")
st.caption(
    f"القيمة النظرية الحسابية للمضاعف المختار: {model['price'] * params['multiplier']:,.2f} "
    "بوحدة العملة نفسها، وليست تكلفة عرض/طلب أو قيمة عقد سوقي."
)

st.subheader("4) تحليل الحساسية الافتراضي")
scenario_range = st.slider("نطاق تغير سعر الأصل حول السعر الحالي (%)", min_value=5, max_value=60, value=20, step=5)
spot_grid = np.linspace(spot * (1 - scenario_range / 100), spot * (1 + scenario_range / 100), 41)
rows = []
for scenario_spot in spot_grid:
    days_left = max(int(params["dte"] * 0.5), 0)
    mark = black_scholes(
        spot=float(scenario_spot), strike=params["strike"], days_to_expiry=days_left,
        volatility=params["iv_pct"] / 100, risk_free_rate=params["rate_pct"] / 100,
        option_type=params["option_type"],
    )["price"]
    intrinsic = expiration_value(float(scenario_spot), params["strike"], params["option_type"])
    rows.append({
        "سعر الأصل في السيناريو": float(scenario_spot),
        f"قيمة نموذجية عند DTE={days_left}": mark,
        "قيمة داخلية عند الانتهاء": intrinsic,
    })
scenario_df = pd.DataFrame(rows)
scenario_fig = go.Figure()
scenario_fig.add_trace(go.Scatter(x=scenario_df["سعر الأصل في السيناريو"], y=scenario_df[f"قيمة نموذجية عند DTE={days_left}"], name=f"قيمة نموذجية عند DTE={days_left}"))
scenario_fig.add_trace(go.Scatter(x=scenario_df["سعر الأصل في السيناريو"], y=scenario_df["قيمة داخلية عند الانتهاء"], name="القيمة الداخلية عند الانتهاء", line={"dash": "dash"}))
scenario_fig.add_vline(x=spot, line_dash="dot", annotation_text="السعر المرجعي")
scenario_fig.add_vline(x=params["strike"], line_dash="dot", annotation_text="Strike الافتراضي")
scenario_fig.update_layout(height=390, xaxis_title="سعر الأصل الافتراضي", yaxis_title="قيمة الخيار لكل وحدة")
st.plotly_chart(scenario_fig, use_container_width=True)
st.dataframe(scenario_df.round(4), use_container_width=True, hide_index=True)

st.subheader("5) القيمة عند الانتهاء — قبل التكاليف")
st.caption("المنحنى التالي يعرض القيمة الداخلية مطروحاً منها القيمة النظرية الحالية كنقطة تعادل حسابية مبسطة؛ لا يتضمن الرسوم أو السبريد أو الضرائب.")
expiry_values = np.array([expiration_value(float(s), params["strike"], params["option_type"]) for s in spot_grid])
simple_pnl = (expiry_values - model["price"]) * params["multiplier"]
pnl_fig = go.Figure()
pnl_fig.add_trace(go.Scatter(x=spot_grid, y=simple_pnl, mode="lines", name="سيناريو حسابي"))
pnl_fig.add_hline(y=0, line_dash="dot")
pnl_fig.add_vline(x=params["strike"], line_dash="dot", annotation_text="Strike الافتراضي")
pnl_fig.update_layout(height=330, xaxis_title="سعر الأصل عند الانتهاء", yaxis_title="فرق القيمة الافتراضي")
st.plotly_chart(pnl_fig, use_container_width=True)

with st.expander("افتراضات النموذج وحدوده"):
    st.markdown("""
- نموذج Black–Scholes مبسط لعقد أوروبي، ولا يمثل كل خصائص الخيارات الأمريكية.
- يفترض تقلباً ثابتاً ومعدل فائدة ثابتاً وعدم وجود توزيعات أرباح.
- لا يحاكي الانحراف الضمني أو سطح التقلب أو تغير السيولة والسبريد.
- لا يستخدم Bid/Ask أو Open Interest أو Volume أو بيانات Greeks من السوق.
- الحساسية تقريبية محلياً، وقد تتغير بسرعة مع السعر والوقت والتقلب.
- لا يشمل التسوية الخاصة بعقود المؤشرات مثل SPX أو فروق المضاعفات الفعلية.
- لا تتضمن الرسوم أو الضرائب أو الانزلاق أو شروط الوسيط.
""")
st.info("لربط سلسلة خيارات فعلية مستقبلاً نحتاج مزوداً موثوقاً ومرخصاً يدعم العقود التاريخية/اللحظية وGreeks، ثم نعرض المصدر ووقت اللقطة وحالة التأخير بوضوح.")
st.caption("Falcon Swing Options · Research and hypothetical simulation only · No broker connection")
