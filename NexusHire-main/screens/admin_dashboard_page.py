import streamlit as st

from components.api_client import (
    admin_delete_candidate,
    admin_delete_session,
    admin_list_candidates,
    admin_list_sessions,
)
from styles.components import pill

# Read-only display of proctoring thresholds — proctoring.py is cheap to
# import (no model loading at import time, unlike backend/session.py, which
# eagerly loads a Whisper model and a Gemini client and has no business
# running inside the Streamlit process).
from proctoring import (
    NO_FACE_WARN_AFTER,
    NO_FACE_TERM_AFTER,
    MULTI_FACE_WARN_AFTER,
    MULTI_FACE_TERM_AFTER,
    LOOK_AWAY_WARN_AFTER,
    LOOK_AWAY_TERM_AFTER,
    MAX_TOTAL_WARNINGS,
)

# Mirrors backend/session.py's constants for display purposes only — not
# imported directly because that module eagerly loads a speech-to-text model
# on import. Source of truth for the real values stays backend/session.py.
INTERVIEW_DURATION_MIN = 10
MAX_CONSECUTIVE_NO_SPEECH = 3


def _header():
    left, right = st.columns([5, 1])
    with left:
        st.markdown(
            """
            <div style="display:flex;align-items:center;gap:10px;">
              <div style="width:36px;height:36px;background:linear-gradient(135deg,#0f766e,#14b8a6);
                          border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:17px;">🧠</div>
              <span style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:20px;color:var(--text);">
                Nexus<span style="color:#0f766e;">Hire</span> — Admin
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if st.button("Log out", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.session_state.admin_page = "login"
            st.rerun()
    st.divider()


def _confirm_delete(row_key: str, warning: str, on_confirm):
    """Two-step delete: shows a Yes/Cancel pair only after the Delete button
    for this specific row was clicked, so a stray click can't wipe data."""
    confirm_key = f"confirm_{row_key}"
    if st.session_state.get(confirm_key):
        st.warning(warning)
        c1, c2 = st.columns(2)
        if c1.button("Yes, delete", key=f"{row_key}_yes", type="primary"):
            on_confirm()
            st.session_state.pop(confirm_key, None)
            st.rerun()
        if c2.button("Cancel", key=f"{row_key}_no"):
            st.session_state.pop(confirm_key, None)
            st.rerun()


def _candidates_tab():
    try:
        candidates = admin_list_candidates()
    except Exception as e:
        st.error(f"Couldn't load candidates: {e}")
        return

    st.caption(f"{len(candidates)} candidate(s)")
    if not candidates:
        st.info("No candidates yet — they show up here once someone completes the details screen.")
        return

    for cand in candidates:
        cid = cand["_id"]
        with st.container(border=True):
            cols = st.columns([2.5, 2.5, 1.8, 1, 1.3, 1])
            cols[0].markdown(f"**{cand.get('name') or '—'}**")
            cols[1].caption(cand.get("email") or "—")
            cols[2].caption(cand.get("university") or "—")
            cols[3].caption(f"CGPA {cand.get('cgpa')}" if cand.get("cgpa") else "—")
            cols[4].markdown(pill("Resume on file", "selected") if cand.get("resume_file_id") else pill("No resume", "pending"), unsafe_allow_html=True)
            if cols[5].button("Delete", key=f"del_cand_{cid}"):
                st.session_state[f"confirm_del_cand_{cid}"] = True
                st.rerun()

            if cand.get("resume_text"):
                with st.expander("Resume text"):
                    st.text(cand["resume_text"])

            _confirm_delete(
                f"del_cand_{cid}",
                f"Delete **{cand.get('name') or cand.get('email')}** and all of their interview sessions? This can't be undone.",
                lambda cid=cid: admin_delete_candidate(cid),
            )


def _sessions_tab():
    try:
        sessions = admin_list_sessions()
    except Exception as e:
        st.error(f"Couldn't load interviews: {e}")
        return

    st.caption(f"{len(sessions)} interview(s)")
    if not sessions:
        st.info("No interviews yet.")
        return

    status_pill = {"completed": "selected", "terminated": "rejected", "in_progress": "live"}

    for sess in sessions:
        sid = sess["_id"]
        with st.container(border=True):
            cols = st.columns([2, 2.5, 2, 1.3, 1, 1])
            cols[0].markdown(f"**{sess.get('candidate_name') or '—'}**")
            cols[1].caption(sess.get("candidate_email") or "—")
            cols[2].caption(f"{sess.get('role') or '—'} · {sess.get('stage') or '—'}")
            cols[3].markdown(pill(sess.get("status", "—"), status_pill.get(sess.get("status"), "pending")), unsafe_allow_html=True)
            cols[4].caption(f"⚠️ {sess.get('total_warnings', 0)}")
            if cols[5].button("Delete", key=f"del_sess_{sid}"):
                st.session_state[f"confirm_del_sess_{sid}"] = True
                st.rerun()

            if sess.get("transcript"):
                with st.expander("Transcript"):
                    st.text(sess["transcript"])

            _confirm_delete(
                f"del_sess_{sid}",
                f"Delete this interview session for **{sess.get('candidate_name') or sess.get('candidate_email')}**? This can't be undone.",
                lambda sid=sid: admin_delete_session(sid),
            )


def _settings_tab():
    st.caption(
        "Read-only for now — these mirror the constants in backend/session.py "
        "and proctoring.py. Editable configuration is a planned next step."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Interview**")
        st.write(f"- Duration: {INTERVIEW_DURATION_MIN} minutes")
        st.write("- Difficulty mode: adaptive (candidate can't choose)")
        st.write(f"- Ends early after {MAX_CONSECUTIVE_NO_SPEECH} consecutive no-response turns")
    with c2:
        st.markdown("**Proctoring thresholds**")
        st.write(f"- No face: warn at {NO_FACE_WARN_AFTER} checks, terminate at {NO_FACE_TERM_AFTER}")
        st.write(f"- Multiple faces: warn at {MULTI_FACE_WARN_AFTER} checks, terminate at {MULTI_FACE_TERM_AFTER}")
        st.write(f"- Looking away: warn at {LOOK_AWAY_WARN_AFTER} checks, terminate at {LOOK_AWAY_TERM_AFTER}")
        st.write(f"- Max total warnings before termination: {MAX_TOTAL_WARNINGS}")


def render():
    _header()
    tab1, tab2, tab3 = st.tabs(["Candidates", "Interviews", "Settings"])
    with tab1:
        _candidates_tab()
    with tab2:
        _sessions_tab()
    with tab3:
        _settings_tab()
