from dotenv import load_dotenv
import streamlit as st

from screens import details_page, setup_page, interview_page, report_page, admin_login_page, admin_dashboard_page
from styles.theme import inject_theme
from styles.components import sidebar_brand

# Loads .env into this (Streamlit) process. The backend process loads its own
# copy independently — this one is what lets the admin login screen and any
# other frontend-side env lookups actually see ADMIN_USERNAME/ADMIN_PASSWORD.
load_dotenv()

# Admin dashboard lives at a separate URL (?admin=1), reached via the small
# "Recruiter / admin login" link on the details screen rather than a button
# in the main candidate flow — it's an internal tool, not part of the
# interview steps themselves.
IS_ADMIN_ROUTE = "admin" in st.query_params

if IS_ADMIN_ROUTE:
    if "admin_page" not in st.session_state:
        st.session_state.admin_page = "login"
else:
    if "page" not in st.session_state:
        st.session_state.page = "details"

st.set_page_config(
    layout="wide",
    page_title="NexusHire Admin" if IS_ADMIN_ROUTE else "NexusHire",
    initial_sidebar_state="collapsed" if (IS_ADMIN_ROUTE or st.session_state.page == "details") else "expanded",
)

inject_theme()

if IS_ADMIN_ROUTE:
    if st.session_state.get("admin_authenticated") and st.session_state.admin_page == "dashboard":
        admin_dashboard_page.render()
    else:
        admin_login_page.render()

else:
    STEP_LABELS = {
        "details": "1 · Your details",
        "setup": "2 · Setup & device check",
        "live": "3 · Live interview",
        "report": "4 · Report",
    }

    with st.sidebar:
        st.markdown(
            sidebar_brand(
                step_label=STEP_LABELS.get(st.session_state.page, ""),
                name=st.session_state.get("candidate_name", ""),
                email=st.session_state.get("candidate_email", ""),
            ),
            unsafe_allow_html=True,
        )

    if st.session_state.page == "details":
        details_page.render()
    elif st.session_state.page == "setup":
        setup_page.render()
    elif st.session_state.page == "live":
        interview_page.render()
    elif st.session_state.page == "report":
        report_page.render()
