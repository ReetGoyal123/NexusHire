import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import uuid
from dataclasses import dataclass
from datetime import datetime

from dotenv import load_dotenv
from faster_whisper import WhisperModel
from google import genai
from google.genai import types

import prompts
from backend.proctor_session import ProctorSession
from backend.stats import compute_speech_stats, aggregate_report_stats

load_dotenv()
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.5-flash"
INTERVIEW_DURATION_SECONDS = 10 * 60
MAX_CONSECUTIVE_NO_SPEECH = 3

END_PHRASES = [
    "goodbye", "all the best", "best of luck",
    "wish you the best", "have a great day",
    "it was a pleasure speaking", "that concludes our interview",
    "this concludes", "take care and good luck",
]

TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp_audio")
os.makedirs(TMP_DIR, exist_ok=True)

_whisper_model = WhisperModel("small", device="cpu", compute_type="int8")


def _transcribe(wav_path: str) -> str:
    try:
        segments, _ = _whisper_model.transcribe(wav_path, beam_size=1, language="en")
        return " ".join(seg.text for seg in segments).strip()
    except Exception as e:
        print(f"[session] Transcription error: {e}")
        return ""


def _is_interview_ending(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in END_PHRASES)


@dataclass
class QARecord:
    n: int
    question: str
    answer: str = ""
    difficulty: int = 2
    speaking_seconds: float = 0.0
    longest_pause_seconds: float = 0.0


class InterviewSession:
    def __init__(
        self,
        role: str,
        stage: str,
        difficulty_mode: str,
        starting_level: int,
        resume_text: str = "",
        candidate_name: str = "",
        candidate_email: str = "",
        candidate_university: str = "",
        candidate_cgpa: str = "",
    ):
        self.id = uuid.uuid4().hex
        self.role = role
        self.stage = stage
        self.difficulty_mode = difficulty_mode
        self.starting_level = starting_level
        self.candidate_name = candidate_name
        self.candidate_email = candidate_email
        self.created_at = time.time()
        self.start_time = time.time()
        self.terminated = False
        self.ended = False
        self.consecutive_no_speech = 0
        self.qa_log: list[QARecord] = []
        self.current_difficulty = starting_level
        self.report_cache = None
        self.proctor = ProctorSession()

        instruction = prompts.build_system_instruction(difficulty_mode, starting_level)
        profile_lines = []
        if candidate_name:
            profile_lines.append(f"Name: {candidate_name}")
        if candidate_university:
            profile_lines.append(f"University: {candidate_university}")
        if candidate_cgpa:
            profile_lines.append(f"CGPA: {candidate_cgpa}")
        if profile_lines:
            instruction += (
                "\n\nCANDIDATE PROFILE (greet them by first name where natural):\n" + "\n".join(profile_lines)
            )
        if resume_text:
            instruction += f"\n\nCANDIDATE RESUME:\n{resume_text}"
        self.chat = _client.chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(system_instruction=instruction),
        )

    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    def start(self) -> dict:
        response = self.chat.send_message(prompts.START_PROMPT)
        text, difficulty = prompts.parse_difficulty((response.text or "").strip(), default=self.starting_level)
        self.current_difficulty = difficulty
        record = QARecord(n=1, question=text, difficulty=difficulty)
        self.qa_log.append(record)
        return {
            "session_id": self.id,
            "question": text,
            "difficulty": difficulty,
            "question_number": record.n,
        }

    def submit_answer(self, wav_bytes: bytes | None) -> dict:
        if self.ended:
            last = self.qa_log[-1]
            return {
                "candidate_text": "",
                "ai_text": "This interview has already ended.",
                "difficulty": self.current_difficulty,
                "question_number": last.n,
                "is_ending": True,
                "terminated": self.terminated,
            }

        record = self.qa_log[-1]

        if not wav_bytes:
            self.consecutive_no_speech += 1
            candidate_text = "[Candidate did not respond — please prompt them again gently]"
            record.answer = ""
        else:
            self.consecutive_no_speech = 0
            wav_path = os.path.join(TMP_DIR, f"{self.id}_{record.n}.wav")
            with open(wav_path, "wb") as f:
                f.write(wav_bytes)
            candidate_text = _transcribe(wav_path)
            speech_stats = compute_speech_stats(wav_path, candidate_text)
            record.answer = candidate_text
            record.speaking_seconds = speech_stats["speaking_seconds"]
            record.longest_pause_seconds = speech_stats["longest_pause_seconds"]
            try:
                os.remove(wav_path)
            except OSError:
                pass
            if not candidate_text.strip():
                candidate_text = "[Candidate's response was inaudible or unintelligible]"

        if self.consecutive_no_speech >= MAX_CONSECUTIVE_NO_SPEECH:
            self.terminated = True
            return self._finish_turn(
                candidate_text,
                "I haven't been able to hear you. Thanks for your time — goodbye!",
                self.current_difficulty,
                terminated=True,
                is_ending=True,
            )

        if self.proctor.terminate:
            self.terminated = True
            return self._finish_turn(
                candidate_text,
                "This interview is being terminated due to multiple security violations.",
                self.current_difficulty,
                terminated=True,
                is_ending=True,
            )

        if self.elapsed_seconds() >= INTERVIEW_DURATION_SECONDS:
            return self._finish_turn(
                candidate_text,
                "We're at time for today — thank you so much for your responses. That concludes our interview, goodbye!",
                self.current_difficulty,
                terminated=False,
                is_ending=True,
            )

        response = self.chat.send_message(candidate_text)
        ai_text, difficulty = prompts.parse_difficulty((response.text or "").strip(), default=self.current_difficulty)
        self.current_difficulty = difficulty
        is_ending = _is_interview_ending(ai_text)

        if not is_ending:
            self.qa_log.append(QARecord(n=record.n + 1, question=ai_text, difficulty=difficulty))

        return self._finish_turn(candidate_text, ai_text, difficulty, terminated=False, is_ending=is_ending)

    def _finish_turn(self, candidate_text: str, ai_text: str, difficulty: int, terminated: bool, is_ending: bool) -> dict:
        if terminated or is_ending:
            self.ended = True
        return {
            "candidate_text": candidate_text,
            "ai_text": ai_text,
            "difficulty": difficulty,
            "question_number": self.qa_log[-1].n,
            "is_ending": is_ending,
            "terminated": terminated,
        }

    def build_report(self) -> dict:
        if self.report_cache is not None:
            return self.report_cache

        report = {
            "candidate_name": self.candidate_name,
            "candidate_email": self.candidate_email,
            "role": self.role,
            "stage": self.stage,
            "date": datetime.fromtimestamp(self.created_at).strftime("%Y-%m-%d %H:%M"),
            "duration_seconds": round(self.elapsed_seconds(), 1),
            "questions": [
                {"n": r.n, "question": r.question, "answer": r.answer, "difficulty": r.difficulty}
                for r in self.qa_log
            ],
            "difficulty_curve": [{"n": r.n, "difficulty": r.difficulty} for r in self.qa_log],
            "proctoring_timeline": self.proctor.timeline,
            "speech_stats": aggregate_report_stats(self.qa_log),
            "total_warnings": self.proctor.warning_count,
        }
        self.report_cache = report
        return report
