"""Thin wrapper around the FastAPI backend (backend/app.py) used by every screen."""
import requests

API_BASE = "http://127.0.0.1:8000"


def start_interview(
    role: str,
    stage: str,
    difficulty_mode: str,
    starting_level: int,
    resume_text: str = "",
    candidate_name: str = "",
    candidate_email: str = "",
    candidate_university: str = "",
    candidate_cgpa: str = "",
) -> dict:
    r = requests.post(
        f"{API_BASE}/api/interview/start",
        json={
            "role": role,
            "stage": stage,
            "difficulty_mode": difficulty_mode,
            "starting_level": starting_level,
            "resume_text": resume_text,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "candidate_university": candidate_university,
            "candidate_cgpa": candidate_cgpa,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def upload_resume(email: str, name: str, filename: str, file_bytes: bytes, content_type: str) -> dict:
    files = {"file": (filename, file_bytes, content_type)}
    r = requests.post(f"{API_BASE}/api/candidates/resume", data={"email": email, "name": name}, files=files, timeout=30)
    r.raise_for_status()
    return r.json()


def submit_answer(session_id: str, wav_bytes: bytes | None) -> dict:
    files = {"audio": ("answer.wav", wav_bytes or b"", "audio/wav")}
    r = requests.post(f"{API_BASE}/api/interview/{session_id}/answer", files=files, timeout=90)
    r.raise_for_status()
    return r.json()


def get_status(session_id: str) -> dict:
    r = requests.get(f"{API_BASE}/api/interview/{session_id}/status", timeout=10)
    r.raise_for_status()
    return r.json()


def end_interview(session_id: str) -> dict:
    r = requests.post(f"{API_BASE}/api/interview/{session_id}/end", timeout=30)
    r.raise_for_status()
    return r.json()


def get_report(session_id: str) -> dict:
    r = requests.get(f"{API_BASE}/api/interview/{session_id}/report", timeout=30)
    r.raise_for_status()
    return r.json()


# ── Admin ─────────────────────────────────────────────────────────────────────

def admin_list_candidates() -> list:
    r = requests.get(f"{API_BASE}/api/admin/candidates", timeout=30)
    r.raise_for_status()
    return r.json()


def admin_list_sessions() -> list:
    r = requests.get(f"{API_BASE}/api/admin/sessions", timeout=30)
    r.raise_for_status()
    return r.json()


def admin_delete_candidate(candidate_id: str) -> None:
    r = requests.delete(f"{API_BASE}/api/admin/candidates/{candidate_id}", timeout=30)
    r.raise_for_status()


def admin_delete_session(session_id: str) -> None:
    r = requests.delete(f"{API_BASE}/api/admin/sessions/{session_id}", timeout=30)
    r.raise_for_status()
