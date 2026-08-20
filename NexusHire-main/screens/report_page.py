import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.api_client import get_report
from styles.components import light_stat_card

TEAL = "#0f766e"
GRID = "#e5e8eb"
STATUS_WARNING = "#b45309"
STATUS_CRITICAL = "#dc2626"


def _difficulty_curve(questions: list[dict]):
    df = pd.DataFrame(questions)
    fig = go.Figure(
        go.Scatter(
            x=df["n"],
            y=df["difficulty"],
            mode="lines+markers",
            line=dict(color=TEAL, width=2),
            marker=dict(size=9, color=TEAL),
            customdata=df["question"].str.slice(0, 80),
            hovertemplate="Q%{x} · Difficulty %{y}/5<br>%{customdata}…<extra></extra>",
        )
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
        xaxis=dict(title="Question #", gridcolor=GRID, dtick=1),
        yaxis=dict(title="Difficulty (1-5)", gridcolor=GRID, range=[0.5, 5.5], dtick=1),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")


def _proctoring_timeline(events: list[dict], duration_seconds: float):
    if not events:
        st.info("No proctoring incidents were flagged during this session.")
        return

    df = pd.DataFrame(events)
    df["minute"] = df["t_seconds"] / 60

    fig = go.Figure()
    for severity, color, label in [("warning", STATUS_WARNING, "⚠️ Warning"), ("critical", STATUS_CRITICAL, "🛑 Critical")]:
        sub = df[df["severity"] == severity]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=sub["minute"],
                y=[0] * len(sub),
                mode="markers",
                name=label,
                marker=dict(size=14, color=color, symbol="circle", line=dict(width=2, color="rgba(0,0,0,0.15)")),
                customdata=sub["type"],
                hovertemplate="%{x:.1f} min · %{customdata}<extra></extra>",
            )
        )

    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=160,
        xaxis=dict(title="Minutes into interview", gridcolor=GRID, range=[0, max(duration_seconds / 60, 1)]),
        yaxis=dict(visible=False, range=[-1, 1]),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")


def render():
    session_id = st.session_state.get("session_id")
    if not session_id:
        st.warning("No completed interview to report on yet.")
        if st.button("← Back to Setup"):
            st.session_state.page = "setup"
            st.rerun()
        return

    try:
        data = get_report(session_id)
    except Exception as e:
        st.error(f"Couldn't load the report: {e}")
        return

    st.title("Interview Report")
    minutes = int(data["duration_seconds"] // 60)
    seconds = int(data["duration_seconds"] % 60)
    who = data.get("candidate_name") or "Candidate"
    st.caption(f"{who} · {data['role']} · {data['stage']} · {data['date']} · {minutes}m {seconds}s")

    st.subheader("Difficulty Curve")
    if data["difficulty_curve"]:
        _difficulty_curve(data["questions"])
        with st.expander("View as table"):
            st.dataframe(pd.DataFrame(data["difficulty_curve"]), hide_index=True, use_container_width=True)
    else:
        st.info("No questions were recorded.")

    st.subheader("Proctoring Timeline")
    _proctoring_timeline(data["proctoring_timeline"], data["duration_seconds"])
    st.caption(f"Total warnings: {data['total_warnings']}")
    if data["proctoring_timeline"]:
        with st.expander("View as table"):
            st.dataframe(pd.DataFrame(data["proctoring_timeline"]), hide_index=True, use_container_width=True)

    st.subheader("Speech Stats")
    stats = data["speech_stats"]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(light_stat_card("💬", "Words / min", str(stats["wpm"] or "–"), ""), unsafe_allow_html=True)
    with c2:
        sub_class = "warn" if stats["filler_count"] > 10 else ""
        st.markdown(light_stat_card("🗯️", "Filler words", str(stats["filler_count"]), "", sub_class), unsafe_allow_html=True)
    with c3:
        st.markdown(light_stat_card("⏱️", "Speaking time", f"{stats['total_speaking_seconds']:.0f}s", ""), unsafe_allow_html=True)
    with c4:
        st.markdown(light_stat_card("⏸️", "Longest pause", f"{stats['longest_pause_seconds']:.1f}s", ""), unsafe_allow_html=True)

    st.subheader("Question & Answer Recap")
    for q in data["questions"]:
        with st.expander(f"Q{q['n']} · Difficulty {q['difficulty']}/5 — {q['question'][:70]}"):
            st.markdown(f"**Question:** {q['question']}")
            st.markdown(f"**Answer:** {q['answer'] or '_(no response)_'}")

    st.divider()
    if st.button("Start a new interview"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
