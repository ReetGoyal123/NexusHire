import time

import streamlit as st

from components.api_client import API_BASE, start_interview
from components.webcam import render_webcam

STAGES = ["Screening", "Technical", "Behavioral"]

# Difficulty progression is the interviewer's job, not the candidate's choice —
# letting candidates pick their own starting difficulty would let them just
# select "easy" and defeat the point of an adaptive assessment. Always run
# adaptive mode; backend/prompts.py raises/lowers difficulty turn-by-turn
# based on answer quality, starting from this fixed opening level.
DIFFICULTY_MODE = "adaptive"
STARTING_LEVEL = 2


def render():
    if not st.session_state.get("candidate_name"):
        st.warning("Please share your details first.")
        if st.button("← Back"):
            st.session_state.page = "details"
            st.rerun()
        return

    st.title("Set up your interview")
    st.caption(f"Welcome, {st.session_state.get('candidate_name', '')} — a couple of quick checks before we start")

    st.subheader("Role & context")
    role = st.text_input(
        "Job role / interview type",
        placeholder="e.g. Backend Developer — Technical Round",
        key="setup_role",
    )
    stage = st.selectbox("Interview stage", STAGES, index=1, key="setup_stage")

    st.subheader("Device check")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🎤 Microphone**")
        test_clip = st.audio_input("Say something to test your mic", key="setup_mic_test")
        if test_clip is not None:
            st.success("Connected")
        else:
            st.warning("Not detected yet")
    with col2:
        st.markdown("**📷 Camera**")
        render_webcam(post_frames=False, height=260, video_height=220)

    st.divider()
    _, right = st.columns([3, 1])
    with right:
        start_clicked = st.button(
            "Start Interview →", type="primary", use_container_width=True, disabled=not role.strip()
        )

    if start_clicked:
        with st.spinner("Connecting to your interviewer..."):
            try:
                result = start_interview(
                    role.strip(),
                    stage,
                    DIFFICULTY_MODE,
                    STARTING_LEVEL,
                    resume_text=st.session_state.get("candidate_resume_text", ""),
                    candidate_name=st.session_state.get("candidate_name", ""),
                    candidate_email=st.session_state.get("candidate_email", ""),
                    candidate_university=st.session_state.get("candidate_university", ""),
                    candidate_cgpa=st.session_state.get("candidate_cgpa", ""),
                )
            except Exception as e:
                st.error(f"Couldn't reach the interview API at {API_BASE}: {e}")
                return

        st.session_state.session_id = result["session_id"]
        st.session_state.role = role.strip()
        st.session_state.stage = stage
        st.session_state.current_question = result["question"]
        st.session_state.current_difficulty = result["difficulty"]
        st.session_state.question_number = result["question_number"]
        st.session_state.transcript_turns = []
        st.session_state.turn_phase = "listening"
        st.session_state.interview_start_ts = time.time()
        st.session_state.page = "live"
        st.rerun()
