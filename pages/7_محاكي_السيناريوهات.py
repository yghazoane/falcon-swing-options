from __future__ import annotations

import plotly.express as px
import streamlit as st

from falcon.auth import require_password
from falcon.market import load_history
from falcon.scenario_simulator import simulate_option_scenarios

st.set_page_config(page_title="Falcon · محاكي السيناريوهات", page_icon="🦅", layout="wide")
require_password()
st.title("محاكي سيناريوهات الخيارات")
st.caption("مختبر افتراضي متعدد العوامل للسعر والوقت والتقلب؛ لا يختار عقوداً ولا يصدر توصيات أو أوامر.")

with st.sidebar:
    symbol = st.text_input("رمز الأصل المرجعي", value="SPY").strip().upper()
    option_type_label = st.selectbox("نوع المثال الافتراضي", ["Call", "Put"])
    option_type = "call" if option_type_label == "Call" else "put"
    period = st.selectbox("فترة السعر المرجعي", ["5d", "1mo", "3mo"], index=1)
    refresh = st.button("تحديث السعر المرجعي", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()

if not symbol:
    st.info("أدخل رمز الأصل.")
    st.stop()

try:
    history = load_history(symbol, period=period, interval="1d")
except Exception as exc:
    st.error(f"تعذر جلب السعر المرجعي: {exc}")
    st.stop()

if history.empty or history["Close"].dropna().empty:
    st.warning("لا يتوفر سعر مرجعي؛ لم يتم إنشاء بيانات بديلة.")
    st.stop()

spot = float(history["Close"].dropna().iloc[-1])
price_time = history["Close"].dropna().index[-1]
st.metric("السعر المرجعي", f"{spot:,.2f}")
st.caption(f"مصدر السعر: Yahoo Finance · تاريخ آخر قيمة: {price_time} · قد تكون البيانات تاريخية أو متأخرة.")

st.subheader("افتراضات السيناريو")
with st.form("scenario_simulation"):
    a, b, c = st.columns(3)
    strike = a.number_input("Strike افتراضي", min_value=0.01, value=float(round(spot, 2)), step=0.5)
    dte = b.number_input("الأيام حتى الانتهاء", min_value=1, max_value=730, value=30)
    iv_pct = c.number_input("التقلب الضمني المفترض %", min_value=1.0, max_value=500.0, value=30.0)
    d, e, f = st.columns(3)
    premium = d.number_input("علاوة افتراضية لكل سهم", min_value=0.0, value=2.0, step=0.05)
    multiplier = e.number_input("مضاعف افتراضي", min_value=1, max_value=10000, value=100)
    contracts = f.number_input("عدد وحدات افتراضية", min_value=1, max_value=1000, value=1)
    rate = st.number_input("معدل فائدة مفترض %", min_value=-5.0, max_value=30.0, value=4.0, step=0.25)
    spot_shocks = st.multiselect("تغير سعر الأصل %", [-40, -30, -20, -10, 0, 10, 20, 30, 40], default=[-20, -10, 0, 10, 20])
    iv_shocks = st.multiselect("تغير التقلب % من الافتراض", [-60, -40, -30, -20, 0, 20, 30, 40, 60], default=[-30, 0, 30])
    elapsed_choices = st.multiselect("الأيام المنقضية", [0, 1, 3, 5, 7, 10, 15, 20, 30, 45, 60, 90], default=[0, 15, 30])
    submitted = st.form_submit_button("إنشاء السيناريوهات", type="primary")

if "falcon_scenario_result" not in st.session_state:
    st.session_state["falcon_scenario_result"] = None

if submitted:
    valid_elapsed = sorted({int(x) for x in elapsed_choices if x <= dte})
    if not spot_shocks or not iv_shocks or not valid_elapsed:
        st.error("اختر قيمة واحدة على الأقل لكل من تغير السعر والتقلب والأيام المنقضية، ضمن مدة العقد.")
    else:
        try:
            st.session_state["falcon_scenario_result"] = simulate_option_scenarios(
                spot=spot, strike=float(strike), days_to_expiry=int(dte),
                volatility=float(iv_pct) / 100, risk_free_rate=float(rate) / 100,
                option_type=option_type, premium_per_share=float(premium),
                multiplier=int(multiplier), contracts=int(contracts),
                spot_changes_pct=[float(x) for x in spot_shocks],
                volatility_changes_pct=[float(x) for x in iv_shocks],
                elapsed_days=valid_elapsed,
            )
        except ValueError as exc:
            st.error(str(exc))

result = st.session_state["falcon_scenario_result"]
if result is not None:
    frame = result["scenarios"]
    st.divider()
    st.subheader("ملخص المحاكاة")
    st.metric("التكلفة الافتراضية المفترضة", f"{result['assumed_initial_cost']:,.2f}")
    st.metric("عدد السيناريوهات", result["scenario_count"])
    st.caption(result["note"])

    selected_elapsed = st.selectbox("عرض منحنى يوم السيناريو", sorted(frame["elapsed_days"].unique()))
    selected_iv = st.selectbox("تغير IV المعروض", sorted(frame["iv_change_pct"].unique()), format_func=lambda x: f"{x:+.0f}%")
    chart_data = frame[(frame["elapsed_days"] == selected_elapsed) & (frame["iv_change_pct"] == selected_iv)].sort_values("scenario_spot")
    fig = px.line(chart_data, x="scenario_spot", y="model_pnl_vs_assumed_premium", markers=True,
                  title="فرق القيمة النموذجية عن العلاوة الافتراضية")
    fig.add_hline(y=0, line_dash="dash")
    fig.update_layout(xaxis_title="سعر الأصل في السيناريو", yaxis_title="فرق القيمة الافتراضي")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("جدول جميع السيناريوهات")
    st.dataframe(frame.round(4), use_container_width=True, hide_index=True)
    csv = frame.to_csv(index=False).encode("utf-8")
    st.download_button("تنزيل نتائج المحاكاة CSV", data=csv, file_name=f"{symbol.lower()}_hypothetical_scenarios.csv", mime="text/csv")
else:
    st.info("أدخل الافتراضات واضغط إنشاء السيناريوهات لعرض النتائج.")

st.warning(
    "القيمة النظرية ليست عرض سعر. النتيجة لا تتضمن تكاليف التنفيذ أو السبريد أو الانزلاق أو الضرائب، "
    "ولا تحاكي بدقة تغير IV عبر آجال وأسعار تنفيذ مختلفة. لا تستخدم هذه المخرجات كتعليمات تداول."
)
