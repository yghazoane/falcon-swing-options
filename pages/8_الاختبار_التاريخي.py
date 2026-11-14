from __future__ import annotations

import pandas as pd
import streamlit as st

from falcon.auth import require_password
from falcon.backtesting import build_historical_observations, walk_forward_validate
from falcon.market import load_history

st.set_page_config(page_title="Falcon · الاختبار التاريخي", page_icon="🦅", layout="wide")
require_password()
st.title("الاختبار التاريخي والتحقق الزمني")
st.caption("اختبار وصفي لقواعد فنية على الأصل الأساسي؛ لا يمثل اختباراً لعقود الخيارات أو ضماناً للأداء المستقبلي.")

with st.sidebar:
    symbol = st.text_input("رمز الأصل", value="SPY").strip().upper()
    period = st.selectbox("الفترة التاريخية", ["2y", "5y", "10y"], index=1)
    horizon = st.selectbox("أفق القياس بالشموع", [1, 3, 5, 10, 20], index=2)
    costs_bps = st.number_input("تكلفة افتراضية لكل ملاحظة (نقاط أساس)", min_value=0.0, max_value=200.0, value=5.0, step=1.0)
    train_fraction = st.slider("نسبة الفترة الأقدم للتطوير", min_value=0.5, max_value=0.9, value=0.7, step=0.05)
    refresh = st.button("تحديث البيانات", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()

if not symbol:
    st.info("أدخل رمزاً.")
    st.stop()

try:
    with st.spinner("تحميل التاريخ السعري وبناء الملاحظات..."):
        history = load_history(symbol, period=period, interval="1d")
        observations = build_historical_observations(
            history, horizon=int(horizon), transaction_cost_bps=float(costs_bps)
        )
        report = walk_forward_validate(observations, train_fraction=float(train_fraction))
except Exception as exc:
    st.error(f"تعذر إكمال الاختبار: {exc}")
    st.stop()

st.warning(
    "الاختبار يستخدم بيانات Yahoo Finance التاريخية وقد تكون معدلة أو ناقصة. "
    "لا توجد هنا سلسلة تاريخية لعقود الخيارات؛ النتائج تقيس عوائد افتراضية على الأصل الأساسي فقط."
)
st.caption(f"عدد الملاحظات: {len(observations)} · بداية فترة الاختبار غير المرئية: {report['split_time']}")

def show_metrics(title: str, metrics: dict):
    st.subheader(title)
    a, b, c = st.columns(3)
    a.metric("عدد الملاحظات", metrics["observations"])
    b.metric("نسبة النتائج الموجبة", f"{metrics['win_rate_pct']:.1f}%" if metrics["win_rate_pct"] is not None else "—")
    c.metric("متوسط العائد لكل ملاحظة", f"{metrics['mean_return_pct']:.3f}%" if metrics["mean_return_pct"] is not None else "—")
    d, e, f = st.columns(3)
    d.metric("العائد التراكمي", f"{metrics['cumulative_return_pct']:.2f}%" if metrics["cumulative_return_pct"] is not None else "—")
    e.metric("أقصى تراجع", f"{metrics['max_drawdown_pct']:.2f}%" if metrics["max_drawdown_pct"] is not None else "—")
    pf = metrics["profit_factor"]
    f.metric("عامل الربح", f"{pf:.2f}" if isinstance(pf, (int, float)) and pd.notna(pf) and pf != float("inf") else ("∞" if pf == float("inf") else "—"))

show_metrics("الفترة الأقدم — التطوير", report["train_metrics"])
show_metrics("الفترة الأحدث — الاختبار الزمني", report["test_metrics"])

st.subheader("توزيع نتائج الاختبار")
test = report["test"].copy()
test["العائد %"] = test["strategy_return"] * 100
st.line_chart(test.set_index("signal_time")["العائد %"].cumsum(), y_label="مجموع العوائد المئوية (تقريبي)")
st.dataframe(
    test[["signal_time", "signal", "entry_time", "entry_price", "exit_time", "exit_price", "strategy_return"]]
    .assign(strategy_return=lambda frame: frame["strategy_return"] * 100)
    .rename(columns={"signal_time": "وقت الإشارة", "signal": "اتجاه القاعدة", "entry_time": "وقت الدخول الافتراضي", "entry_price": "سعر الدخول", "exit_time": "وقت الخروج الافتراضي", "exit_price": "سعر الخروج", "strategy_return": "العائد الصافي %"}),
    use_container_width=True, hide_index=True,
)
st.caption(report["method_note"])
st.info(
    "هذه مرحلة تحقق بحثي أولية وليست إثباتاً لاستراتيجية مربحة. "
    "توجد فترات احتفاظ متداخلة وقد لا تكون الملاحظات مستقلة؛ كما لا تشمل النتائج "
    "تسعير الخيارات أو IV skew أو Greeks أو فروق أسعار الخيارات أو العمولات الخاصة بها."
)
