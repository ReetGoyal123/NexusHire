import time

import streamlit as st

from components.api_client import API_BASE, end_interview, get_status, submit_answer
from components.guard import render_guard
from components.tts import speak
from components.webcam import render_webcam
from styles.components import _flatten

VAD_LABELS = {
    "listening": ("🎙️ Listening", "green"),
    "processing": ("🤖 Processing your answer...", "blue"),
    "done": ("✅ Interview complete", "gray"),
}

APPROX_TOTAL_QUESTIONS = 6


def _reveal_transcript(placeholder, text: str):
    if not text:
        placeholder.markdown("> _(no response captured)_")
        return
    words = text.split()
    shown = []
    for w in words:
        shown.append(w)
        placeholder.markdown(f"> {' '.join(shown)}")
        time.sleep(0.02)


def render():
    session_id = st.session_state.get("session_id")
    if not session_id:
        st.warning("No active interview session. Please start from the Setup screen.")
        if st.button("← Back to Setup"):
            st.session_state.page = "setup"
            st.rerun()
        return

    st.title("AI Interview")
    ended = st.session_state.get("interview_ended", False)
    qn = st.session_state.get("question_number", 1)

    speak(st.session_state.get("current_question", ""))
    if not ended:
        render_guard(session_id, API_BASE)

    left, right = st.columns([2, 1], gap="large")

    with left:
        st.markdown(f"##### Question {qn} of ~{APPROX_TOTAL_QUESTIONS}")
        question_text = st.session_state.get('current_question', '')
        st.markdown(
            _flatten(f"""
            <div style="padding:28px;border-radius:14px;background:var(--surface3);color:var(--text);
                        text-align:center;font-size:1.35rem;font-weight:600;min-height:90px;
                        display:flex;align-items:center;justify-content:center;">
                {question_text}
            </div>
            """),
            unsafe_allow_html=True,
        )

        phase = "done" if ended else st.session_state.get("turn_phase", "listening")
        label, color = VAD_LABELS[phase]
        st.markdown(f":{color}[**{label}**]")

        st.markdown("###### Your answer")
        audio_val, skip = None, False
        if not ended:
            audio_val = st.audio_input("Record your answer", key=f"answer_audio_{qn}", label_visibility="collapsed")
            skip = st.button("Skip / I don't know", key=f"skip_{qn}")

        st.markdown("###### Live transcript")
        transcript_box = st.container(height=220, border=True)
        with transcript_box:
            for turn in st.session_state.get("transcript_turns", []):
                st.markdown(f"**Q{turn['n']}:** {turn['question']}")
                st.markdown(f"_You:_ {turn['answer'] or '(no response)'}")
                st.markdown("---")
            live_placeholder = st.empty()

        if not ended and (audio_val is not None or skip):
            st.session_state.turn_phase = "processing"
            wav_bytes = None if skip else audio_val.getvalue()
            with st.spinner("Transcribing and thinking..."):
                try:
                    result = submit_answer(session_id, wav_bytes)
                except Exception as e:
                    st.error(f"Couldn't reach the interview API: {e}")
                    return

            _reveal_transcript(live_placeholder, result["candidate_text"])

            st.session_state.transcript_turns.append(
                {"n": qn, "question": st.session_state.current_question, "answer": result["candidate_text"]}
            )
            st.session_state.current_question = result["ai_text"]
            st.session_state.current_difficulty = result["difficulty"]
            st.session_state.question_number = result["question_number"]
            st.session_state.turn_phase = "listening"

            if result["is_ending"] or result["terminated"]:
                st.session_state.interview_ended = True

            st.rerun()

        if ended:
            st.success("The interview has ended.")
            if st.button("View Report →", type="primary"):
                with st.spinner("Building your report..."):
                    try:
                        end_interview(session_id)
                    except Exception as e:
                        st.error(f"Couldn't finalize the interview: {e}")
                        return
                st.session_state.page = "report"
                st.rerun()

    with right:
        st.markdown("###### 📷 Proctoring")
        render_webcam(session_id=session_id, api_base=API_BASE, height=300, video_height=260)

        try:
            status = get_status(session_id)
        except Exception:
            status = None

        if status:
            face_icon = "✓" if status["face_detected"] else "✗"
            gaze_label = "On-screen" if status["gaze"] == "on-screen" else f"Deviated ({status['gaze']})"
            multi_label = "Flagged" if status["multi_face"] else "Clear"
            st.markdown(f"**Face detected:** {face_icon}")
            st.markdown(f"**Gaze status:** {gaze_label}")
            st.markdown(f"**Multi-face check:** {multi_label}")
            warn_color = (
                "red"
                if status["warning_count"] >= status["max_warnings"] - 1
                else ("orange" if status["warning_count"] > 0 else "green")
            )
            st.markdown(f":{warn_color}[**{status['warning_count']} / {status['max_warnings']} warnings**]")

            if status["terminate"] and not ended:
                st.session_state.interview_ended = True
                st.rerun()
        else:
            st.caption("Waiting for proctoring status...")

    if not ended:
        time.sleep(2)
        st.rerun()
