from __future__ import annotations

import hmac
import os
import streamlit as st


def require_password() -> None:
    """Fail closed unless a private app password is configured."""
    expected = os.getenv("FALCON_APP_PASSWORD", "")
    if not expected:
        try:
            expected = st.secrets.get("app_password", "")
        except Exception:
            expected = ""
    if not expected:
        st.error("التطبيق مقفل لحماية الخصوصية. اضبط FALCON_APP_PASSWORD أو app_password في إعدادات الأسرار.")
        st.code('FALCON_APP_PASSWORD = "كلمة_مرور_قوية_وفريدة"', language="text")
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
