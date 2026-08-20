import streamlit as st

from components.api_client import upload_resume

MAX_RESUME_MB = 8


def _extract_resume_text(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(uploaded_file)
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    return uploaded_file.getvalue().decode("utf-8", errors="ignore")


def render():
    st.markdown("""
    <style>
    /* Stretch both hero columns to fill the viewport height instead of
       shrinking to their (short) content height. */
    div[data-testid="stHorizontalBlock"]:has(.details-left) {
        min-height: 100vh;
        align-items: stretch;
    }
    div[data-testid="column"]:has(.details-left) {
        padding: 0 !important;
    }
    .details-left {
        background: #0f172a;
        color: white;
        height: 100%;
        min-height: 100vh;
        margin: -1rem 0 -1rem -1rem;
        padding: 60px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
    }
    .details-title { font-size: 32px; font-weight: 800; margin-bottom: 6px; }
    .details-sub { color: #64748b; margin-bottom: 22px; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1.1], gap="large")

    with col1:
        st.markdown("""
        <div class="details-left">
            <div>
                <h2>Nexus<span style="color:#5eead4;">Hire</span></h2>
            </div>
            <div>
                <h1>Interview smarter,<br>hire better.</h1>
                <p style="color:#94a3b8;">
                AI-powered interviews with real-time analysis and scoring.
                </p>
            </div>
            <div style="color:#64748b;font-size:13px;">
                Resume-aware AI • Live proctoring • Auto scoring
            </div>
            <div style="margin-top:14px;">
                <a href="?admin=1" target="_self" style="color:#5eead4;font-size:12px;text-decoration:none;border-bottom:1px dotted rgba(94,234,212,0.5);">
                    Recruiter / admin login →
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="details-title">Before we begin</div>', unsafe_allow_html=True)
        st.markdown('<div class="details-sub">Tell us a bit about you</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full name *", key="details_name", placeholder="Jane Doe")
            university = st.text_input("University / College", key="details_university")
        with c2:
            email = st.text_input("Email *", key="details_email", placeholder="you@example.com")
            cgpa = st.text_input("CGPA (optional)", key="details_cgpa")

        resume_file = st.file_uploader("Resume (optional, PDF or TXT)", type=["pdf", "txt"], key="details_resume")

        consent = st.checkbox(
            "I consent to sharing the details above and to being recorded via camera and microphone, "
            "with automated proctoring, for the duration of this interview.",
            key="details_consent",
        )
        st.caption(
            "This is an AI-conducted screening interview. To keep it fair to candidates who interview "
            "in person, your camera, microphone, and screen focus are monitored throughout."
        )

        email_valid = "@" in email and "." in email.split("@")[-1] if email else False
        ready = bool(name.strip()) and email_valid and consent

        if (name or email) and not ready:
            missing = []
            if not name.strip():
                missing.append("full name")
            if not email_valid:
                missing.append("a valid email")
            if not consent:
                missing.append("consent")
            st.caption(f"Please provide: {', '.join(missing)}.")

        if st.button("Continue →", type="primary", disabled=not ready, use_container_width=True):
            resume_text = _extract_resume_text(resume_file)
            st.session_state.candidate_name = name.strip()
            st.session_state.candidate_email = email.strip()
            st.session_state.candidate_university = university.strip()
            st.session_state.candidate_cgpa = cgpa.strip()
            st.session_state.candidate_resume_text = resume_text

            if resume_file is not None:
                try:
                    upload_resume(
                        email=email.strip(),
                        name=name.strip(),
                        filename=resume_file.name,
                        file_bytes=resume_file.getvalue(),
                        content_type=resume_file.type or "application/octet-stream",
                    )
                except Exception as e:
                    st.warning(f"Resume text was captured, but the original file couldn't be stored: {e}")

            st.session_state.page = "setup"
            st.rerun()
