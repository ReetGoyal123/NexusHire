# NexusHire — AI Mock Interview Platform

NexusHire is an AI-powered mock interview platform. A candidate fills in their details,
uploads a resume, does a mic/camera check, and then has a live, ~10-minute spoken interview
with an LLM-driven interviewer ("Alex") that adapts question difficulty to their answers in
real time. While the interview runs, the candidate's own browser streams webcam frames for
face/gaze proctoring and watches for fullscreen exits, tab switches, and copy attempts. At
the end, the candidate gets a Plotly-charted report (difficulty curve, proctoring timeline,
speech stats, full transcript). A separate, password-gated admin/recruiter dashboard lets
someone browse and delete candidates and interview sessions.

All mic and webcam capture happens natively in the candidate's own browser (via
`st.audio_input` and `getUserMedia`) and is sent to the backend over HTTP — no media ever
touches the server's local hardware, so the app can be hosted for real, remote candidates.

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup (Windows / VS Code)](#setup-windows--vs-code)
- [Setup (macOS / Linux)](#setup-macos--linux)
- [Environment Variables](#environment-variables)
- [Running the App](#running-the-app)
- [Admin / Recruiter Dashboard](#admin--recruiter-dashboard)
- [Database](#database)
- [API Overview](#api-overview)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Known Limitations](#known-limitations)
- [License](#license)

---

## Architecture

```
app.py (router)
  │
  ├─ candidate flow (default route)
  │    ├─ screens/details_page.py   candidate details, resume upload, consent
  │    ├─ screens/setup_page.py     role/stage/difficulty, mic+cam check
  │    ├─ screens/interview_page.py live interview: transcript, proctoring, guard
  │    └─ screens/report_page.py    Plotly difficulty curve + proctoring timeline
  │
  └─ admin flow (?admin=1 in the URL)
       ├─ screens/admin_login_page.py      username+password gate
       └─ screens/admin_dashboard_page.py  Candidates / Interviews / Settings tabs,
                                          delete with confirm, read-only config

components/                  browser-native building blocks
  ├─ api_client.py           REST client → backend/app.py (candidate + admin)
  ├─ webcam.py                getUserMedia preview + periodic frame POST
  ├─ guard.py                 fullscreen/tab-switch/copy anti-cheat
  └─ tts.py                   browser SpeechSynthesis (question read-aloud)

backend/                     FastAPI REST API (run separately, port 8000)
  ├─ app.py                  routes: start / answer / status / proctor
  │                          frame / violation / end / report / resume /
  │                          admin (list + delete candidates & sessions)
  ├─ session.py               Gemini chat loop, adaptive difficulty, QA log
  ├─ stats.py                 speech stats (WPM, fillers, pauses) from audio
  ├─ proctor_session.py       per-session face/gaze detection (reuses
  │                           proctoring.py's cascade + gaze helpers)
  └─ db.py                    MongoDB: candidates, sessions, resumes (GridFS)

proctoring.py, prompts.py    shared core logic
styles/                      "Slate & Teal" theme + reusable components
```

Both processes run locally against MongoDB.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend UI | Streamlit |
| Backend API | FastAPI + Uvicorn |
| LLM interviewer | Google Gemini (`google-genai`, `gemini-2.5-flash`) |
| Speech-to-text | `faster-whisper` ("small" model, CPU) |
| Computer vision / proctoring | OpenCV (Haar cascade face detection) |
| Charts / reporting | Plotly + Pandas |
| Database | MongoDB via Motor (async driver) + GridFS for resume files |
| Resume parsing | `pypdf` |

---

## Prerequisites

- **Python 3.10 – 3.12**
- **MongoDB** running locally (`mongod`), or a MongoDB Atlas connection string
- A **Gemini API key** ([Google AI Studio](https://aistudio.google.com/))
- A working **microphone and webcam** — used in the *candidate's browser*, not by the server
- (Windows only) **VS Code** recommended, with the Python extension

---

## Setup (Windows / VS Code)

```powershell
cd path\to\NexusHire-main
python -m venv .venv
.venv\Scripts\Activate.ps1

:: If PowerShell blocks the script with an execution-policy error, run this once:
::   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
:: then re-run the Activate.ps1 line above.

pip install --upgrade pip
pip install -r requirements.txt

copy .env.example .env
:: then edit .env — see Environment Variables below
```

> **OpenCV note:** `requirements.txt` pins `opencv-python<5.0.0`. If you see
> `AttributeError: module 'cv2' has no attribute 'CascadeClassifier'`, run:
> `pip install "opencv-python<5.0.0" --force-reinstall`

---

## Setup (macOS / Linux)

```bash
cd path/to/NexusHire-main
python -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
# then edit .env — see Environment Variables below
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
GEMINI_API_KEY=your_gemini_api_key_here

# MongoDB — defaults work for a local `mongod` with no auth.
# For MongoDB Atlas, use the connection string from your cluster's "Connect" dialog.
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=nexushire

# Recruiter/admin dashboard login — basic username+password check, not a
# real auth system (no hashing, no sessions beyond Streamlit's own state).
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me
```

**Change `ADMIN_PASSWORD` before sharing the app with anyone.**

---

## Running the App

The backend and frontend are two independent processes — **both must be running**
at the same time, in two separate terminals.

**Terminal 1 — API + DB:**

```powershell
# Windows
.venv\Scripts\Activate.ps1
python -m uvicorn backend.app:app --reload --port 8000
```

```bash
# macOS / Linux
source .venv/bin/activate
uvicorn backend.app:app --reload --port 8000
```

> On Windows, use `python -m uvicorn ...` rather than the bare `uvicorn ...` command —
> otherwise the `--reload` subprocess can fail to see the project root on `sys.path` and
> raise `ModuleNotFoundError: No module named 'backend'` even when run from the correct
> folder. See [Troubleshooting](#troubleshooting).

Verify it's up at `http://127.0.0.1:8000/docs` (FastAPI's Swagger UI).

**Terminal 2 — frontend:**

```powershell
# Windows
.venv\Scripts\Activate.ps1
streamlit run app.py
```

```bash
# macOS / Linux
source .venv/bin/activate
streamlit run app.py
```

Streamlit opens `http://localhost:8501` automatically. Allow camera/microphone permissions
when the browser prompts you.

Requires a running MongoDB (`mongod` locally, or an Atlas connection string in `.env`).

---

## Admin / Recruiter Dashboard

Visit `http://localhost:8501/?admin=1` instead of the plain app URL. Log in with
`ADMIN_USERNAME` / `ADMIN_PASSWORD` from `.env`. From there:

- **Candidates** — every candidate profile, resume text, and a Delete button (with a
  confirm step) that removes the candidate, their resume file, and all of their interview
  sessions.
- **Interviews** — every session with status/warnings and the full transcript, individually
  deletable.
- **Settings** — read-only view of the current interview duration, difficulty mode, and
  proctoring thresholds. Not editable yet.

This is intentionally basic — a real user/role system, editable config, and API-level auth
on the `/api/admin/*` routes (currently gated only by the Streamlit login screen, same as
everything else in this app) are natural next steps once there's a clearer idea of what's
actually needed.

---

## Database

MongoDB collections (see `backend/db.py` for the full schema):

- **`candidates`** — one document per unique email: name, university, CGPA, parsed resume
  text, and a `resume_file_id` pointing into GridFS.
- **`sessions`** — one document per interview: candidate ref, role/stage, full Q&A
  transcript, proctoring timeline, speech stats, status.
- **`resumes`** (GridFS bucket) — the original uploaded PDF/TXT file.

---

## API Overview

All routes live in `backend/app.py`, served at `http://127.0.0.1:8000`.

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/interview/start` | Start a new interview session |
| `POST` | `/api/interview/{session_id}/answer` | Submit a recorded answer (WAV) |
| `GET` | `/api/interview/{session_id}/status` | Poll proctoring / elapsed-time status |
| `POST` | `/api/interview/{session_id}/proctor/frame` | Submit a webcam frame for face/gaze analysis |
| `POST` | `/api/interview/{session_id}/violation` | Report a browser-side anti-cheat violation |
| `POST` | `/api/interview/{session_id}/end` | End the interview and build the report |
| `GET` | `/api/interview/{session_id}/report` | Fetch the final report |
| `POST` | `/api/candidates/resume` | Upload the original resume file to GridFS |
| `GET` | `/api/admin/candidates` | List all candidates |
| `GET` | `/api/admin/sessions` | List all interview sessions |
| `DELETE` | `/api/admin/candidates/{candidate_id}` | Delete a candidate (cascades) |
| `DELETE` | `/api/admin/sessions/{session_id}` | Delete a session |

Full interactive docs at `http://127.0.0.1:8000/docs` while the backend is running.

---

## Project Structure

```
NexusHire-main/
├── app.py                          # Router: candidate flow, or admin flow behind ?admin=1
├── proctoring.py                   # Shared face/gaze detection core
├── prompts.py                      # Gemini system prompt + [DIFFICULTY:n] tag parsing
├── requirements.txt
├── .env.example
├── .streamlit/config.toml          # Forces light theme
├── backend/
│   ├── app.py                      # FastAPI routes (candidate + /api/admin/*)
│   ├── session.py                  # Gemini chat loop, adaptive difficulty, QA log
│   ├── stats.py                    # Speech stats derived from answer audio
│   ├── proctor_session.py          # Per-session face/gaze proctoring (browser frames)
│   └── db.py                       # MongoDB schema + candidate/session/resume persistence
├── components/
│   ├── api_client.py               # REST client used by every page
│   ├── webcam.py                   # Browser webcam capture + frame upload
│   ├── guard.py                    # Fullscreen/tab-switch/copy anti-cheat
│   └── tts.py                      # Browser text-to-speech for the AI's questions
├── screens/
│   ├── details_page.py             # Name/email/university/CGPA/resume/consent
│   ├── setup_page.py                # Role, stage, difficulty mode, device check
│   ├── interview_page.py           # Live transcript, proctoring, guard, End button
│   ├── report_page.py               # Difficulty curve, proctoring timeline, speech stats
│   ├── admin_login_page.py         # Username/password gate for the admin flow
│   └── admin_dashboard_page.py     # Candidates / Interviews / Settings tabs
└── styles/
    ├── theme.py                    # "Slate & Teal" CSS tokens
    └── components.py               # Reusable component builders
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `AttributeError: module 'cv2' has no attribute 'CascadeClassifier'` | `requirements.txt` pins `opencv-python<5.0.0` because OpenCV 5.0 removed the classic `CascadeClassifier` API that `proctoring.py` depends on. If you've already got 5.x installed: `pip install "opencv-python<5.0.0" --force-reinstall` |
| `ModuleNotFoundError: No module named 'backend'` when starting Uvicorn (Windows) | Use `python -m uvicorn backend.app:app --reload --port 8000` instead of the bare `uvicorn ...` command — this ensures the project root is on `sys.path` for the `--reload` subprocess. Also confirm you're running it from the project root itself, not a nested `NexusHire-main\NexusHire-main\` folder left over from extracting the zip. |
| `Activate.ps1 cannot be loaded because running scripts is disabled` (Windows) | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. |
| Backend can't connect to Mongo (`ServerSelectionTimeoutError`) | Confirm `mongod`/the MongoDB service is running (`mongosh` should connect), or check your Atlas `MONGODB_URI` and IP allow-list. |
| Streamlit says it can't reach the interview API | Make sure the backend (Uvicorn on port 8000) is still running — frontend and backend are independent processes and both must be up. |
| Camera/mic not detected in-browser | Check the browser's site permissions for `localhost:8501` (camera + microphone must both be allowed), and make sure no other app is holding the webcam. |

---

## Known Limitations

- **No real authentication anywhere.** The candidate details screen is personalization, not
  login. The admin login is a plaintext username/password check against `.env`, with no
  hashing, sessions, or rate limiting, and the `/api/admin/*` endpoints themselves have no
  auth — only the Streamlit login screen gates them. Fine for local/single-admin use; not
  for real deployment.
- **In-memory interview state.** Live `InterviewSession`/proctoring state lives only in the
  backend process's memory until an interview ends — a backend restart loses any
  in-progress interview, and horizontal scaling would need sticky sessions or externalized
  state (e.g. Redis).
- **Admin settings are read-only.** Interview duration, difficulty defaults, and proctoring
  thresholds are shown but not editable from the dashboard yet.
- **No automated tests.**

---
