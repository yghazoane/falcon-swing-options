from __future__ import annotations

import hmac
import streamlit as st


def require_password() -> None:
    """Fail closed unless a deployment password is configured in Streamlit secrets."""
    try:
        expected = st.secrets.get("app_password", "")
    except Exception:
        expected = ""
    if not expected:
        st.error("التطبيق مقفل لحماية الخصوصية. أضف app_password إلى Streamlit Secrets قبل الاستخدام.")
        st.code('app_password = "ضع_كلمة_مرور_قوية_هنا"', language="toml")
        st.stop()
    if st.session_state.get("falcon_authenticated") is True:
        return
    st.subheader("دخول خاص")
    with st.form("falcon_login"):
        supplied = st.text_input("كلمة المرور", type="password")
        submitted = st.form_submit_button("دخول")
    if submitted:
        if hmac.compare_digest(str(supplied), str(expected)):
            st.session_state["falcon_authenticated"] = True
            st.rerun()
        st.error("كلمة المرور غير صحيحة.")
    st.stop()
