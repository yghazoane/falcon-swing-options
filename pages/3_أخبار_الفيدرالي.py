from __future__ import annotations

import streamlit as st
import pandas as pd

from falcon.auth import require_password
from falcon.fed_news import load_fed_news
from falcon.news_impact import classify_news_impact

st.set_page_config(page_title="Falcon · أخبار الفيدرالي", page_icon="🦅", layout="wide")
require_password()
st.title("أخبار وبيانات الاحتياطي الفيدرالي")
st.caption("مصدر رسمي: موجز الأخبار والبيانات الصحفية لمجلس الاحتياطي الفيدرالي الأمريكي.")

if st.button("تحديث الأخبار"):
    load_fed_news.clear()

try:
    with st.spinner("تحميل موجز الاحتياطي الفيدرالي..."):
        result = load_fed_news()
except Exception as exc:
    st.error(f"تعذر الوصول إلى موجز الفيدرالي: {exc}")
    st.stop()

st.caption(f"آخر جلب من المصدر: {result['retrieved_at_utc']}")
st.caption(f"المصدر المستخدم: {result.get('source_label', 'Federal Reserve RSS')}")
if result.get("notice"):
    st.info(result["notice"])

items = result["items"]
if not items:
    st.info("لم يعرض الموجز عناصر حالياً.")
else:
    st.subheader("ملخص الأثر المحتمل")
    enriched = [{**item, **classify_news_impact(item)} for item in items]
    summary = pd.DataFrame(enriched)
    counts = summary["label"].value_counts()
    cols = st.columns(4)
    labels = [
        "إيجابي محتمل للأسواق",
        "سلبي محتمل للأسواق",
        "محايد / لا توجد إشارة واضحة",
        "مختلط / غير واضح",
    ]
    for col, label in zip(cols, labels):
        col.metric(label, int(counts.get(label, 0)))

    for item in enriched:
        impact = item["impact"]
        icon = {
            "potentially_supportive": "🟢",
            "potentially_adverse": "🔴",
            "neutral": "⚪",
            "mixed_or_unclear": "🟡",
        }[impact]
        st.markdown(f"### {icon} {item['label']}")
        st.markdown(f"**{item['title']}**")
        if item.get("published"):
            st.caption(item["published"])
        st.write(f"**سبب التصنيف:** {item['reason']}")
        st.caption(
            f"الثقة: {item['confidence']} · {item['method']}"
        )
        if item.get("description"):
            st.write(item["description"])
        st.link_button("فتح البيان الرسمي", item["link"])
        st.divider()

st.warning(
    "التصنيف آلي أولي يعتمد على كلمات مفتاحية، وقد يخطئ في فهم السياق أو نبرة البيان. "
    "إيجابية الخبر اقتصادياً لا تعني بالضرورة ارتفاع الأسهم؛ فقد يختلف الأثر حسب التوقعات "
    "والتقييمات والعوائد والظروف السائدة. لا يُستخدم التصنيف كإشارة تداول."
)
st.caption("هذا موجز بيانات صحفية، وليس تقويماً اقتصادياً شاملاً ولا تنبيهاً فورياً لكل حدث أو خطاب.")
