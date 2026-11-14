from __future__ import annotations

import streamlit as st
from falcon.auth import require_password
from falcon.fed_news import load_fed_news

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
    for item in items:
        st.markdown(f"**{item['title']}**")
        if item.get("published"):
            st.caption(item["published"])
        if item.get("description"):
            st.write(item["description"])
        st.link_button("فتح البيان الرسمي", item["link"])
        st.divider()

st.caption("هذا موجز بيانات صحفية، وليس تقويماً اقتصادياً شاملاً ولا تنبيهاً فورياً لكل حدث أو خطاب.")
