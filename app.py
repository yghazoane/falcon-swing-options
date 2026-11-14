from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from falcon.auth import require_password
from falcon.context import summarize_market_context
from falcon.fibonacci import latest_fibonacci_levels
from falcon.indicators import add_indicators
from falcon.market import load_history
from falcon.market_intelligence import build_market_intelligence
from falcon.fed_news import load_fed_news, FedFeedError
from falcon.news_impact import classify_news_impact
from falcon.multi_timeframe import load_multi_timeframe
from falcon.scoring import describe_confluence
from falcon.structure import describe_market_structure
from falcon.universe import load_us_equity_universe
from falcon.volume_profile import volume_by_price

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
    if st.button("تحديث جميع بيانات السوق", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

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
last_bar_time = frame.index[-1]

tab_market, tab_universe, tab_asset, tab_options, tab_method = st.tabs(["السوق العام", "دليل الأسهم الأمريكية", "تحليل الرمز", "مفاهيم الخيارات", "المنهجية والبيانات"])
with tab_market:
    st.subheader("محرك قراءة السوق العام")
    with st.spinner("تجميع المؤشرات والتقلب والقطاعات والمتغيرات الكلية..."):
        intelligence = build_market_intelligence()
    m1, m2, m3 = st.columns(3)
    m1.metric("حالة السوق الوصفية", intelligence["regime"])
    m2.metric("ثقة التصنيف", intelligence["confidence"])
    m3.metric("آخر تاريخ بيانات متاح", intelligence["latest_data_date"] or "غير متاح")
    st.caption(intelligence["method_note"])
    st.info(intelligence["data_note"])
    st.markdown("**المؤشرات الرئيسية وبدائل المتابعة**")
    indices_df = pd.DataFrame(intelligence["indices"])
    st.dataframe(indices_df, use_container_width=True, hide_index=True)
    st.markdown("**مشاركة القطاعات والقوة النسبية مقابل SPY خلال 20 جلسة**")
    participation = intelligence["sector_participation"]
    st.caption(
        f"القطاعات المتاحة: {participation['available_sectors']} · "
        f"موجبة خلال 20 جلسة: {participation['positive_20d']} · "
        f"سالبة: {participation['negative_20d']}"
    )
    st.dataframe(pd.DataFrame(intelligence["sectors"]), use_container_width=True, hide_index=True)
    st.markdown("**المتغيرات الكلية البديلة**")
    st.dataframe(pd.DataFrame(intelligence["macro"]), use_container_width=True, hide_index=True)
    st.markdown("**أخبار الاحتياطي الفيدرالي وتصنيف أثرها المحتمل**")
    try:
        news_payload = load_fed_news()
        st.caption(f"المصدر: {news_payload.get('source_label')} · جلبت في: {news_payload.get('retrieved_at_utc')}")
        if news_payload.get("notice"):
            st.warning(str(news_payload["notice"]))
        news_rows = []
        for item in news_payload.get("items", [])[:8]:
            impact = classify_news_impact(item)
            news_rows.append({
                "تاريخ النشر": item.get("published") or "غير متاح",
                "الخبر": item.get("title", ""),
                "الأثر المحتمل": impact["label"],
                "الثقة": impact["confidence"],
                "سبب التصنيف": impact["reason"],
                "الرابط": item.get("link", ""),
            })
        if news_rows:
            st.dataframe(pd.DataFrame(news_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("لا توجد عناوين متاحة حالياً.")
    except FedFeedError as exc:
        st.warning(f"تعذر تحميل أخبار الفيدرالي حالياً: {exc}")
    st.subheader("قراءة فنية متعددة الأطر الزمنية")
    with st.spinner("تحليل اليومي والساعة و4 ساعات المشتقة..."):
        mtf_rows, mtf_alignment = load_multi_timeframe(symbol)
    st.metric("ملخص توافق الأطر", mtf_alignment["label"])
    st.caption(mtf_alignment["note"])
    mtf_table = pd.DataFrame(mtf_rows)[[
        "timeframe", "trend", "momentum", "macd_state", "volume_state",
        "structure", "structure_event", "close", "rsi14", "bars", "source"
    ]].rename(columns={
        "timeframe": "الإطار", "trend": "الاتجاه", "momentum": "الزخم",
        "macd_state": "MACD", "volume_state": "الحجم", "structure": "هيكل السوق",
        "structure_event": "حدث الهيكل", "close": "الإغلاق", "rsi14": "RSI 14",
        "bars": "عدد الشموع", "source": "مصدر الإطار"
    })
    st.dataframe(mtf_table, use_container_width=True, hide_index=True)
    st.caption("إطار 4 ساعات مشتق من شموع الساعة وليس إطاراً أصلياً من المزود. المقارنة وصفية، وتتجاهل الأطر التي لا تتوفر لها بيانات كافية.")
with tab_universe:
    st.subheader("دليل رموز الأسهم المدرجة")
    st.caption("يتم تحميل دليل Nasdaq Trader لقوائم Nasdaq والأسواق الأخرى، مع استبعاد رموز الاختبار. لا يشمل هذا الدليل جميع أوراق OTC ولا يعني أن كل رمز له بيانات تاريخية متاحة.")
    if st.button("تحديث دليل الرموز"):
        load_us_equity_universe.clear()
    try:
        with st.spinner("تحميل دليل الرموز..."):
            universe = load_us_equity_universe()
        st.metric("عدد الرموز المدرجة المتاحة في الدليل", f"{len(universe):,}")
        query = st.text_input("ابحث بالرمز أو اسم الشركة", key="universe_search").strip().upper()
        if query:
            matches = universe[
                universe["symbol"].str.contains(query, case=False, na=False)
                | universe["security_name"].str.contains(query, case=False, na=False)
            ].head(100)
        else:
            matches = universe.head(100)
        st.dataframe(matches, use_container_width=True, hide_index=True)
        if not matches.empty:
            chosen = st.selectbox("اختر رمزاً للتحليل", matches["symbol"].tolist())
            if st.button("استخدام الرمز في التحليل"):
                st.session_state["selected_universe_symbol"] = chosen
                st.success(f"تم اختيار {chosen}. أدخله في حقل الرمز في الشريط الجانبي.")
    except Exception as exc:
        st.warning(f"تعذر تحميل دليل الرموز حالياً: {exc}. يمكنك إدخال الرمز يدوياً.")
with tab_asset:
    st.subheader(f"{symbol} — السعر والمؤشرات")
    st.caption(f"آخر شمعة أعادها المصدر: {last_bar_time} · قد تكون البيانات متأخرة أو غير مكتملة.")
    a, b, c, d = st.columns(4)
    a.metric("آخر إغلاق", f"{last['Close']:,.2f}")
    b.metric("EMA 20", f"{last['EMA20']:,.2f}" if pd.notna(last["EMA20"]) else "—")
    c.metric("RSI 14", f"{last['RSI14']:.1f}" if pd.notna(last["RSI14"]) else "—")
    d.metric("ATR 14", f"{last['ATR14']:.2f}" if pd.notna(last["ATR14"]) else "—")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=frame.index, open=frame["Open"], high=frame["High"], low=frame["Low"], close=frame["Close"], name=symbol))
    for col, label in (("EMA20", "EMA 20"), ("EMA50", "EMA 50"), ("EMA200", "EMA 200"), ("VWAP", "VWAP")):
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
    st.subheader("الحجم وVWAP")
    volume_fig = go.Figure()
    volume_fig.add_trace(go.Bar(x=frame.index, y=frame["Volume"], name="Volume"))
    volume_fig.update_layout(height=220, margin={"l": 10, "r": 10, "t": 20, "b": 10})
    st.plotly_chart(volume_fig, use_container_width=True)
    st.caption("VWAP محسوب من شموع المزود؛ في اليومي/الأسبوعي يكون متوسطاً مرجعياً تراكمياً للفترة، وفي البيانات داخل اليوم يعاد ضبطه حسب التاريخ.")
    profile = volume_by_price(frame)
    if not profile.empty:
        profile_fig = go.Figure(go.Bar(x=profile["volume"], y=profile["price_level"], orientation="h", name="Volume by price (proxy)"))
        profile_fig.update_layout(height=360, xaxis_title="حجم تقريبي", yaxis_title="مستوى السعر", margin={"l": 10, "r": 10, "t": 20, "b": 10})
        st.plotly_chart(profile_fig, use_container_width=True)
    st.caption("توزيع الحجم حسب السعر تقريبي باستخدام السعر النموذجي لكل شمعة، وليس Volume Profile حقيقياً مبنياً على كل صفقة.")
    st.subheader("مستويات Fibonacci المرجعية")
    if fib["levels"]:
        st.caption(f"اتجاه الساق: {fib['direction']} · النطاق: {fib['swing_low']:.2f} — {fib['swing_high']:.2f}")
        st.markdown("**Retracement — ارتدادات**")
        st.dataframe([{"النسبة": k, "المستوى": round(v, 4)} for k, v in fib["levels"].items()], use_container_width=True, hide_index=True)
        if fib.get("extensions"):
            st.markdown("**Extensions — امتدادات**")
            st.dataframe([{"النسبة": k, "المستوى": round(v, 4)} for k, v in fib["extensions"].items()], use_container_width=True, hide_index=True)
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
