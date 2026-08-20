"""Per-session, web-friendly wrapper around proctoring.py's detection logic.

The CLI flow in proctoring.py owns a single global camera thread + cv2.imshow window.
Here each InterviewSession gets its own ProctorSession instance; frames arrive one at a
time as JPEG snapshots posted from the browser instead of being pulled from a local
cv2.VideoCapture, but the face/gaze streak thresholds and warning escalation logic are
identical to the CLI path.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np

from proctoring import (
    _load_cascade,
    _detect_faces,
    _gaze_direction,
    NO_FACE_WARN_AFTER,
    NO_FACE_TERM_AFTER,
    MULTI_FACE_WARN_AFTER,
    MULTI_FACE_TERM_AFTER,
    LOOK_AWAY_WARN_AFTER,
    LOOK_AWAY_TERM_AFTER,
    MAX_TOTAL_WARNINGS,
)

MAX_TIMELINE_EVENTS = 200


class ProctorSession:
    def __init__(self):
        self.cascade = _load_cascade()
        self.no_face_streak = 0
        self.multi_face_streak = 0
        self.look_away_streak = 0
        self.warning_count = 0
        self.terminate = False
        self.status = "Starting..."
        self.face_detected = False
        self.gaze = "on-screen"
        self.multi_face = False
        self.timeline = []
        self.start_time = time.time()

    def analyze_frame(self, frame: np.ndarray):
        frame_h, frame_w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = _detect_faces(gray, self.cascade, frame_w)
        n = len(faces)
        issued = None
        severity = "info"

        if n == 0:
            self.no_face_streak += 1
            self.multi_face_streak = 0
            self.look_away_streak = 0
            self.face_detected = False
            self.multi_face = False
            self.status = f"No face ({self.no_face_streak}/{NO_FACE_WARN_AFTER})"
            if self.no_face_streak == NO_FACE_WARN_AFTER:
                issued, severity = "No face detected - please stay in frame", "warning"
            elif self.no_face_streak >= NO_FACE_TERM_AFTER:
                issued, severity = "Candidate absent - interview terminated", "critical"
                self.terminate = True

        elif n > 1:
            self.multi_face_streak += 1
            self.no_face_streak = 0
            self.look_away_streak = 0
            self.face_detected = True
            self.multi_face = True
            self.status = f"Multiple faces ({n})"
            if self.multi_face_streak == MULTI_FACE_WARN_AFTER:
                issued, severity = f"Multiple people detected ({n} faces)", "warning"
            elif self.multi_face_streak >= MULTI_FACE_TERM_AFTER:
                issued, severity = "Interview terminated - multiple people in frame", "critical"
                self.terminate = True

        else:
            self.no_face_streak = 0
            self.multi_face_streak = 0
            self.face_detected = True
            self.multi_face = False
            direction = _gaze_direction(faces[0], frame_w, frame_h)
            if direction:
                self.look_away_streak += 1
                self.gaze = direction
                self.status = f"Looking {direction} ({self.look_away_streak}/{LOOK_AWAY_WARN_AFTER})"
                if self.look_away_streak == LOOK_AWAY_WARN_AFTER:
                    issued, severity = f"Please look at the screen (looking {direction})", "warning"
                elif self.look_away_streak >= LOOK_AWAY_TERM_AFTER:
                    issued, severity = "Interview terminated - prolonged inattention", "critical"
                    self.terminate = True
            else:
                self.look_away_streak = 0
                self.gaze = "on-screen"
                self.status = "OK"

        if issued:
            self._issue(issued, severity)

    def report_violation(self, message: str, severity: str = "warning"):
        """For non-camera 'unfair means' signals (fullscreen exit, tab switch, copy attempt)
        reported directly by the browser — no grace streak, every occurrence counts."""
        self._issue(message, severity)

    def _issue(self, message: str, severity: str):
        self.warning_count += 1
        if len(self.timeline) < MAX_TIMELINE_EVENTS:
            self.timeline.append(
                {
                    "t_seconds": round(time.time() - self.start_time, 1),
                    "type": message,
                    "severity": severity,
                }
            )
        if self.warning_count >= MAX_TOTAL_WARNINGS:
            self.terminate = True

    def status_payload(self) -> dict:
        return {
            "warning_count": self.warning_count,
            "max_warnings": MAX_TOTAL_WARNINGS,
            "terminate": self.terminate,
            "status_message": self.status,
            "face_detected": self.face_detected,
            "gaze": self.gaze,
            "multi_face": self.multi_face,
        }
