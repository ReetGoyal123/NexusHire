"""Speech stats derived offline from an answer's WAV file + its transcript.

There is no live VAD stream from the browser recorder (unlike the CLI's record_with_vad),
so pauses/speaking-time are recovered after the fact via the same RMS-over-blocks approach
audio.py uses for its silence threshold.
"""
import re

import numpy as np
from scipy.io.wavfile import read as read_wav

SILENCE_THRESHOLD = 0.015  # matches audio.py's RMS silence threshold
BLOCK_MS = 100

FILLER_WORDS = [
    "um", "umm", "uh", "uhh", "like", "you know", "actually",
    "basically", "i mean", "sort of", "kind of",
]
_FILLER_PATTERNS = [re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE) for w in FILLER_WORDS]


def compute_speech_stats(wav_path: str, transcript: str) -> dict:
    """Returns {speaking_seconds, longest_pause_seconds} for a single answer's audio."""
    try:
        fs, data = read_wav(wav_path)
    except Exception:
        return {"speaking_seconds": 0.0, "longest_pause_seconds": 0.0}

    samples = data.astype(np.float32)
    if data.dtype == np.int16:
        samples /= 32768.0
    elif data.dtype == np.int32:
        samples /= 2147483648.0
    if samples.ndim > 1:
        samples = samples.mean(axis=1)

    block_size = max(1, int(fs * BLOCK_MS / 1000))
    n_blocks = len(samples) // block_size

    speaking_blocks = 0
    longest_silence_blocks = 0
    current_silence_blocks = 0
    started = False

    for i in range(n_blocks):
        block = samples[i * block_size : (i + 1) * block_size]
        rms = np.sqrt(np.mean(block**2))
        if rms > SILENCE_THRESHOLD:
            started = True
            speaking_blocks += 1
            current_silence_blocks = 0
        elif started:
            current_silence_blocks += 1
            longest_silence_blocks = max(longest_silence_blocks, current_silence_blocks)

    return {
        "speaking_seconds": round(speaking_blocks * BLOCK_MS / 1000, 2),
        "longest_pause_seconds": round(longest_silence_blocks * BLOCK_MS / 1000, 2),
    }


def count_filler_words(transcript: str) -> int:
    return sum(len(pattern.findall(transcript)) for pattern in _FILLER_PATTERNS)


def aggregate_report_stats(qa_log) -> dict:
    total_speaking = sum(r.speaking_seconds for r in qa_log)
    total_words = sum(len(r.answer.split()) for r in qa_log if r.answer)
    longest_pause = max((r.longest_pause_seconds for r in qa_log), default=0.0)
    filler_count = sum(count_filler_words(r.answer) for r in qa_log if r.answer)
    wpm = round(total_words / (total_speaking / 60), 1) if total_speaking > 0 else 0.0

    return {
        "wpm": wpm,
        "filler_count": filler_count,
        "total_speaking_seconds": round(total_speaking, 1),
        "longest_pause_seconds": round(longest_pause, 2),
    }
