from __future__ import annotations

import pandas as pd
import streamlit as st

from falcon.auth import require_password
from falcon.market import load_history
from falcon.options_data import get_option_expirations, load_options_chain
from falcon.contract_screening import rank_contract_data_quality
from falcon.market_intelligence import build_market_intelligence
from falcon.multi_timeframe import load_multi_timeframe
from falcon.fed_news import FedFeedError, load_fed_news
from falcon.news_impact import classify_news_impact
from falcon.stock_analysis import analyze_stock_frame
from falcon.research_ranking import rank_paper_candidates

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

if refresh:
    st.cache_data.clear()
    st.rerun()

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
market_context = None
timeframe_rows = []
timeframe_alignment = {"label": "غير متاح"}
stock_report = None
try:
    with st.spinner("قراءة اتجاه المؤشرات والأطر الزمنية..."):
        market_context = build_market_intelligence()
        timeframe_rows, timeframe_alignment = load_multi_timeframe(symbol)
        stock_history = load_history(symbol, period="1y", interval="1d")
        stock_report = analyze_stock_frame(stock_history)
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
    st.markdown("**ملخص التحليل الفني للأصل**")
    st.metric("الحالة الفنية", stock_report["descriptive_state"])
    st.caption(
        f"آخر شمعة: {stock_report['as_of']} · "
        f"مكونات إيجابية: {stock_report['bullish_components']} · "
        f"مكونات سلبية: {stock_report['bearish_components']}"
    )
    st.markdown("**آخر أخبار الاحتياطي الفيدرالي**")
    try:
        fed_payload = load_fed_news()
        news_rows = []
        for item in fed_payload.get("items", [])[:5]:
            impact = classify_news_impact(item)
            news_rows.append({
                "تاريخ النشر": item.get("published") or "غير متاح",
                "العنوان": item.get("title", ""),
                "الأثر النصي المحتمل": impact["label"],
                "مستوى الثقة": impact["confidence"],
                "الرابط": item.get("link", ""),
            })
        if news_rows:
            st.dataframe(pd.DataFrame(news_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("لا توجد عناوين متاحة حالياً.")
    except FedFeedError as news_exc:
        st.caption(f"تعذر تحميل أخبار الفيدرالي: {news_exc}")
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


st.divider()
st.subheader("قائمة المرشحين للبحث والمحاكاة")
if market_context is not None and stock_report is not None:
    candidates = rank_paper_candidates(
        screened.get("calls", pd.DataFrame()),
        screened.get("puts", pd.DataFrame()),
        market_context=market_context,
        stock_report=stock_report,
        timeframe_alignment=timeframe_alignment,
        top_n=10,
    )
    if candidates.empty:
        st.info("لا توجد عقود اجتازت جميع مرشحات جودة البيانات مع توفر مكونات التصنيف الحالية.")
    else:
        candidate_columns = [
            "option_type", "contractSymbol", "mid", "strike", "daysToExpiry",
            "delta", "spread_pct_mid", "volume", "openInterest",
            "research_fit_score", "research_fit_label",
        ]
        candidate_labels = {
            "option_type": "النوع", "contractSymbol": "رمز العقد",
            "mid": "Mid تقريبي", "strike": "Strike",
            "daysToExpiry": "DTE", "delta": "Delta نموذجي",
            "spread_pct_mid": "السبريد %", "volume": "الحجم",
            "openInterest": "Open Interest",
            "research_fit_score": "درجة التوافق البحثي",
            "research_fit_label": "وصف التوافق",
        }
        st.dataframe(
            candidates[candidate_columns].rename(columns=candidate_labels),
            use_container_width=True,
            hide_index=True,
        )
        with st.expander("تفاصيل أسباب ترتيب كل مرشح"):
            st.dataframe(
                candidates[["contractSymbol", "option_type", "research_fit_reasons"]].rename(columns={
                    "contractSymbol": "رمز العقد",
                    "option_type": "النوع",
                    "research_fit_reasons": "تفاصيل المكونات",
                }),
                use_container_width=True,
                hide_index=True,
            )
        st.caption(
            "درجة التوافق من 100 هي درجة مطابقة موزونة لمعايير البحث الحالية وليست احتمال نجاح أو ربح. "
            "الترتيب لا يعني أن العقد مناسب للشراء، ولا يصدر أمراً أو توصية تنفيذ."
        )
else:
    st.info("تعذر بناء قائمة الترتيب لأن بعض بيانات السوق أو التحليل الفني غير متاحة. لا يتم استنتاج اتجاه بديل.")

st.info(
    "درجة جودة البيانات تقيس اكتمال العرض والسبريد والحجم وOpen Interest وIV وDTE والسعر الوسطي وفق الحدود التي تختارها. "
    "لا تقيس اتجاه السوق أو احتمالية الربح أو ملاءمة العقد للشراء؛ النتائج قائمة مراقبة افتراضية للبحث والمحاكاة فقط."
)
