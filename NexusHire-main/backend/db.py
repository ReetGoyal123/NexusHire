"""
MongoDB layer: candidate profiles, interview sessions, and resume files.

Uses Motor (async) since the rest of the API is FastAPI/async-friendly.

Schema
──────
candidates (one document per unique email)
    _id             ObjectId
    name            str
    email           str            — unique index
    university      str
    cgpa            str
    resume_text     str            — latest parsed resume text
    resume_file_id  ObjectId|None  — GridFS id of the latest uploaded resume file
    created_at      datetime
    updated_at      datetime

sessions (one document per interview session; _id == InterviewSession.id)
    _id                  str            — uuid hex, same id used in the REST API URLs
    candidate_id         ObjectId       — ref -> candidates._id
    candidate_name       str            — snapshot at interview time
    candidate_email      str            — snapshot at interview time
    role                 str
    stage                str
    difficulty_mode      str
    starting_level       int
    status               "in_progress" | "completed" | "terminated"
    created_at           datetime
    ended_at             datetime|None
    duration_seconds     float
    qa_log               [{n, question, answer, difficulty,
                            speaking_seconds, longest_pause_seconds}]
    transcript           str            — flattened "AI: ...\\nCandidate: ...\\n" text
    proctoring_timeline  [{t_seconds, type, severity}]
    total_warnings       int
    speech_stats         {wpm, filler_count, total_speaking_seconds, longest_pause_seconds}

resumes — GridFS bucket ("resumes")
    original uploaded PDF/TXT bytes, filename, content_type,
    metadata: {candidate_id, uploaded_at}
"""
import os
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "nexushire")

_client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGODB_URI)
    return _client


def get_db():
    return get_client()[MONGODB_DB_NAME]


def get_resume_bucket() -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(get_db(), bucket_name="resumes")


async def ensure_indexes():
    """Call once at startup (see app.py's startup event)."""
    db = get_db()
    await db.candidates.create_index("email", unique=True)
    await db.sessions.create_index("candidate_id")
    await db.sessions.create_index("created_at")


# ── Candidates ────────────────────────────────────────────────────────────────

async def upsert_candidate(
    name: str,
    email: str,
    university: str = "",
    cgpa: str = "",
    resume_text: str = "",
) -> ObjectId:
    """Create or update the candidate profile keyed by email. Returns candidate _id."""
    db = get_db()
    now = datetime.now(timezone.utc)
    update: dict = {
        "$set": {
            "name": name,
            "email": email,
            "university": university,
            "cgpa": cgpa,
            "updated_at": now,
        },
        "$setOnInsert": {"created_at": now},
    }
    if resume_text:
        update["$set"]["resume_text"] = resume_text

    result = await db.candidates.find_one_and_update(
        {"email": email},
        update,
        upsert=True,
        return_document=True,
    )
    return result["_id"]


async def save_resume_file(
    candidate_id: ObjectId, filename: str, content_type: str, file_bytes: bytes
) -> ObjectId:
    """Stores the original resume file in GridFS and links it to the candidate."""
    bucket = get_resume_bucket()
    file_id = await bucket.upload_from_stream(
        filename,
        file_bytes,
        metadata={
            "candidate_id": candidate_id,
            "content_type": content_type,
            "uploaded_at": datetime.now(timezone.utc),
        },
    )
    db = get_db()
    await db.candidates.update_one(
        {"_id": candidate_id}, {"$set": {"resume_file_id": file_id}}
    )
    return file_id


async def get_candidate_by_email(email: str) -> Optional[dict]:
    return await get_db().candidates.find_one({"email": email})


async def list_candidates(limit: int = 200) -> list:
    """For the recruiter dashboard: all candidate profiles, newest first."""
    cursor = get_db().candidates.find({}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def delete_candidate(candidate_id: ObjectId) -> None:
    """Removes a candidate and everything tied to them: their resume file
    (if any) and all of their interview sessions. Used by the recruiter
    dashboard's delete action — a full removal, not a soft-delete, since
    that's what "delete this candidate's details" means to a recruiter."""
    db = get_db()
    candidate = await db.candidates.find_one({"_id": candidate_id})
    if candidate and candidate.get("resume_file_id"):
        bucket = get_resume_bucket()
        try:
            await bucket.delete(candidate["resume_file_id"])
        except Exception:
            pass  # file already gone / never fully uploaded — not fatal
    await db.sessions.delete_many({"candidate_id": candidate_id})
    await db.candidates.delete_one({"_id": candidate_id})


# ── Sessions ──────────────────────────────────────────────────────────────────

async def create_session(
    session_id: str,
    candidate_id: ObjectId,
    candidate_name: str,
    candidate_email: str,
    role: str,
    stage: str,
    difficulty_mode: str,
    starting_level: int,
) -> None:
    db = get_db()
    await db.sessions.insert_one(
        {
            "_id": session_id,
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "role": role,
            "stage": stage,
            "difficulty_mode": difficulty_mode,
            "starting_level": starting_level,
            "status": "in_progress",
            "created_at": datetime.now(timezone.utc),
            "ended_at": None,
            "duration_seconds": 0.0,
            "qa_log": [],
            "transcript": "",
            "proctoring_timeline": [],
            "total_warnings": 0,
            "speech_stats": {},
        }
    )


async def finalize_session(session_id: str, report: dict, terminated: bool = False) -> None:
    """Persists the final report produced by InterviewSession.build_report()."""
    transcript_lines = []
    for q in report["questions"]:
        transcript_lines.append(f"AI: {q['question']}")
        if q["answer"]:
            transcript_lines.append(f"Candidate: {q['answer']}")

    db = get_db()
    await db.sessions.update_one(
        {"_id": session_id},
        {
            "$set": {
                "status": "terminated" if terminated else "completed",
                "ended_at": datetime.now(timezone.utc),
                "duration_seconds": report["duration_seconds"],
                "qa_log": report["questions"],
                "transcript": "\n".join(transcript_lines),
                "proctoring_timeline": report["proctoring_timeline"],
                "total_warnings": report["total_warnings"],
                "speech_stats": report["speech_stats"],
            }
        },
    )


async def get_session(session_id: str) -> Optional[dict]:
    return await get_db().sessions.find_one({"_id": session_id})


async def list_candidate_sessions(candidate_id: ObjectId, limit: int = 50) -> list:
    cursor = (
        get_db()
        .sessions.find({"candidate_id": candidate_id})
        .sort("created_at", -1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def list_recent_sessions(limit: int = 50) -> list:
    """For a recruiter dashboard: most recent interviews across all candidates."""
    cursor = get_db().sessions.find({}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def delete_session(session_id: str) -> None:
    await get_db().sessions.delete_one({"_id": session_id})
