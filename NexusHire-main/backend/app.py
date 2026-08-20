import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
from typing import Optional

import cv2
import numpy as np
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend import db
from backend.session import InterviewSession

app = FastAPI(title="NexusHire Interview API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    await db.ensure_indexes()


_SESSIONS: dict[str, InterviewSession] = {}
_LOCK = threading.Lock()


def _get_session(session_id: str) -> InterviewSession:
    with _LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


class StartRequest(BaseModel):
    role: str
    stage: str = "Technical"
    difficulty_mode: str = "adaptive"
    starting_level: int = 2
    resume_text: str = ""
    candidate_name: str = ""
    candidate_email: str = ""
    candidate_university: str = ""
    candidate_cgpa: str = ""


@app.post("/api/interview/start")
async def start_interview(req: StartRequest):
    if not req.role.strip():
        raise HTTPException(status_code=400, detail="role is required")
    session = InterviewSession(
        role=req.role.strip(),
        stage=req.stage,
        difficulty_mode=req.difficulty_mode,
        starting_level=req.starting_level,
        resume_text=req.resume_text,
        candidate_name=req.candidate_name,
        candidate_email=req.candidate_email,
        candidate_university=req.candidate_university,
        candidate_cgpa=req.candidate_cgpa,
    )
    with _LOCK:
        _SESSIONS[session.id] = session
    result = session.start()

    if req.candidate_email:
        candidate_id = await db.upsert_candidate(
            name=req.candidate_name,
            email=req.candidate_email,
            university=req.candidate_university,
            cgpa=req.candidate_cgpa,
            resume_text=req.resume_text,
        )
        await db.create_session(
            session_id=session.id,
            candidate_id=candidate_id,
            candidate_name=req.candidate_name,
            candidate_email=req.candidate_email,
            role=session.role,
            stage=session.stage,
            difficulty_mode=session.difficulty_mode,
            starting_level=session.starting_level,
        )

    return result


@app.post("/api/interview/{session_id}/answer")
def submit_answer(session_id: str, audio: Optional[UploadFile] = File(None)):
    session = _get_session(session_id)
    wav_bytes = audio.file.read() if audio is not None else None
    return session.submit_answer(wav_bytes or None)


@app.get("/api/interview/{session_id}/status")
def get_status(session_id: str):
    session = _get_session(session_id)
    payload = session.proctor.status_payload()
    payload["elapsed_seconds"] = round(session.elapsed_seconds(), 1)
    payload["question_number"] = session.qa_log[-1].n if session.qa_log else 0
    payload["ended"] = session.ended
    return payload


@app.post("/api/interview/{session_id}/proctor/frame")
def proctor_frame(session_id: str, frame: UploadFile = File(...)):
    session = _get_session(session_id)
    contents = frame.file.read()
    arr = np.frombuffer(contents, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is not None:
        session.proctor.analyze_frame(img)
    return {"status": "ok"}


@app.post("/api/interview/{session_id}/violation")
def report_violation(session_id: str, violation_type: str = Form(..., alias="type"), message: str = Form(...)):
    session = _get_session(session_id)
    session.proctor.report_violation(message, severity="warning")
    return session.proctor.status_payload()


@app.post("/api/interview/{session_id}/end")
async def end_interview(session_id: str):
    session = _get_session(session_id)
    session.ended = True
    report = session.build_report()
    if session.candidate_email:
        await db.finalize_session(session_id, report, terminated=session.terminated)
    return {"ok": True, "report": report}


@app.post("/api/candidates/resume")
async def upload_resume(email: str = Form(...), name: str = Form(""), file: UploadFile = File(...)):
    """Stores the original resume file in GridFS, linked to the candidate by email.
    Call this alongside /api/interview/start (which only carries parsed resume_text)
    if you want the original PDF/TXT kept, not just the extracted text."""
    if not email.strip():
        raise HTTPException(status_code=400, detail="email is required")
    candidate_id = await db.upsert_candidate(name=name, email=email)
    file_bytes = await file.read()
    file_id = await db.save_resume_file(
        candidate_id, file.filename, file.content_type or "application/octet-stream", file_bytes
    )
    return {"candidate_id": str(candidate_id), "resume_file_id": str(file_id)}


@app.get("/api/interview/{session_id}/report")
def get_report(session_id: str):
    session = _get_session(session_id)
    return session.build_report()


# ── Admin (recruiter dashboard) ─────────────────────────────────────────────
# No auth at this layer yet — access is gated by the Streamlit admin login
# screen only, same "no real auth" honesty as the candidate flow (see README).

def _serialize_doc(doc: dict) -> dict:
    """Mongo ObjectIds aren't JSON-serializable on their own; stringify them."""
    out = dict(doc)
    for key in ("_id", "candidate_id", "resume_file_id"):
        if out.get(key) is not None:
            out[key] = str(out[key])
    return out


def _parse_object_id(raw_id: str) -> ObjectId:
    try:
        return ObjectId(raw_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid id")


@app.get("/api/admin/candidates")
async def admin_list_candidates():
    candidates = await db.list_candidates()
    return [_serialize_doc(c) for c in candidates]


@app.get("/api/admin/sessions")
async def admin_list_sessions():
    sessions = await db.list_recent_sessions()
    return [_serialize_doc(s) for s in sessions]


@app.delete("/api/admin/candidates/{candidate_id}")
async def admin_delete_candidate(candidate_id: str):
    await db.delete_candidate(_parse_object_id(candidate_id))
    return {"ok": True}


@app.delete("/api/admin/sessions/{session_id}")
async def admin_delete_session(session_id: str):
    await db.delete_session(session_id)
    return {"ok": True}
