import os

import streamlit as st


def render():
    st.markdown(
        """
        <div style="max-width:360px;margin:80px auto 0;text-align:center;">
          <div style="width:48px;height:48px;margin:0 auto 16px;background:linear-gradient(135deg,#0f766e,#14b8a6);
                      border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:22px;">🧠</div>
          <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:22px;color:var(--text);">
            Nexus<span style="color:#0f766e;">Hire</span> Admin
          </div>
          <div style="color:var(--muted2);font-size:14px;margin-top:4px;">Recruiter dashboard sign-in</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        with st.form("admin_login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

        if submitted:
            real_username = os.getenv("ADMIN_USERNAME", "")
            real_password = os.getenv("ADMIN_PASSWORD", "")
            if not real_username or not real_password:
                st.error("Admin login isn't configured — set ADMIN_USERNAME and ADMIN_PASSWORD in .env.")
            elif username == real_username and password == real_password:
                st.session_state.admin_authenticated = True
                st.session_state.admin_page = "dashboard"
                st.rerun()
            else:
                st.error("Incorrect username or password.")
