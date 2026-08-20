"""
proctoring.py — optimized for low CPU usage
─────────────────────────────────────────────────────────────────────────────
KEY OPTIMIZATION: Detection and display are now decoupled.
  - Capture thread: reads camera frames at ~15fps, pushes raw frames to queue
  - Analysis: runs only every CHECK_INTERVAL_SEC on the latest frame
  - Display: main thread shows whatever is in the queue — never blocks
  - No more Haar cascade running 30x per second killing the CPU
─────────────────────────────────────────────────────────────────────────────
NOTE for Streamlit: The cv2.imshow proctoring window runs in a separate
OS window alongside the Streamlit browser tab.  Call close_display() on
interview end or when shared_state["terminate"] is set.
─────────────────────────────────────────────────────────────────────────────
"""

import cv2
import time
import queue
import threading

# ── Tunables ────────────────────────────────────────────────────────────────
STARTUP_GRACE_PERIOD  = 8.0
CAMERA_INDEX          = 0
CHECK_INTERVAL_SEC    = 2.0   # analysis runs this often, NOT every frame
CAPTURE_FPS_LIMIT     = 15    # cap capture rate to save CPU

NO_FACE_WARN_AFTER    = 8
NO_FACE_TERM_AFTER    = 20
MULTI_FACE_WARN_AFTER = 3
MULTI_FACE_TERM_AFTER = 8
LOOK_AWAY_WARN_AFTER  = 6
LOOK_AWAY_TERM_AFTER  = 15
MAX_TOTAL_WARNINGS    = 5

MIN_FACE_WIDTH_RATIO  = 0.06
MIN_NEIGHBORS         = 4
SCALE_FACTOR          = 1.2   # faster than 1.15, still accurate enough
GAZE_X_THRESHOLD      = 0.42
GAZE_Y_THRESHOLD      = 0.38
# ────────────────────────────────────────────────────────────────────────────

# Raw frames for display (main thread reads these)
_display_queue = queue.Queue(maxsize=2)
_stop_event    = threading.Event()

# Shared annotation state written by analysis, read by display
_annotation_lock   = threading.Lock()
_annotation_state  = {"faces": [], "warning_count": 0, "status": "Starting..."}


# ── Main-thread display API ───────────────────────────────────────────────────

def show_pending_frame() -> bool:
    """Call from MAIN THREAD. Shows latest frame. Returns False if ESC pressed."""
    try:
        frame = _display_queue.get_nowait()
        # Annotate on the copy before showing
        with _annotation_lock:
            faces         = _annotation_state["faces"]
            warning_count = _annotation_state["warning_count"]
            status        = _annotation_state["status"]

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        color = (0, 200, 0) if warning_count == 0 else (0, 165, 255)
        if warning_count >= MAX_TOTAL_WARNINGS:
            color = (0, 0, 255)

        cv2.putText(frame, f"Warnings: {warning_count}/{MAX_TOTAL_WARNINGS}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, status,
                    (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        cv2.imshow("AI Interview - Proctoring", frame)
    except queue.Empty:
        pass

    return (cv2.waitKey(1) & 0xFF) != 27


def close_display():
    """Call from main thread to shut down display."""
    _stop_event.set()
    cv2.destroyAllWindows()
    cv2.waitKey(1)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_cascade():
    path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(path)
    if cascade.empty():
        raise RuntimeError("Haar cascade not found. pip install --upgrade opencv-python")
    return cascade


def _detect_faces(gray, cascade, frame_w):
    rects = cascade.detectMultiScale(
        gray,
        scaleFactor=SCALE_FACTOR,
        minNeighbors=MIN_NEIGHBORS,
        minSize=(int(frame_w * MIN_FACE_WIDTH_RATIO),
                 int(frame_w * MIN_FACE_WIDTH_RATIO)),
    )
    return [] if len(rects) == 0 else list(rects)


def _gaze_direction(face_rect, frame_w, frame_h):
    x, y, w, h = face_rect
    norm_x = ((x + w / 2) - frame_w / 2) / (frame_w / 2)
    norm_y = ((y + h / 2) - frame_h / 2) / (frame_h / 2)
    if abs(norm_x) > GAZE_X_THRESHOLD:
        return "right" if norm_x > 0 else "left"
    if norm_y < -GAZE_Y_THRESHOLD:
        return "up"
    if norm_y > GAZE_Y_THRESHOLD:
        return "down"
    return None


# ── Background thread ─────────────────────────────────────────────────────────

def start_proctoring(shared_state: dict):
    print("[Proctor] Starting...")

    try:
        cascade = _load_cascade()
    except AttributeError:
        # cv2 module is present but missing core attributes (e.g.
        # CascadeClassifier) — almost always a broken/conflicting OpenCV
        # install (opencv-python + opencv-python-headless installed
        # together, or a corrupted wheel), not a code bug.
        print(
            "[Proctor] FATAL - Your OpenCV install looks broken "
            "(cv2 has no CascadeClassifier). Fix with:\n"
            "  pip uninstall opencv-python opencv-python-headless "
            "opencv-contrib-python -y\n"
            "  pip install --no-cache-dir opencv-python\n"
            "Proctoring is disabled for this session; the interview will "
            "still run without webcam monitoring."
        )
        return
    except RuntimeError as e:
        print(f"[Proctor] FATAL - {e}")
        return
    except Exception as e:
        print(f"[Proctor] FATAL - unexpected error loading face detector: {e}")
        return

    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        print("[Proctor] ERROR - Could not open webcam.")
        return

    frame_interval = 1.0 / CAPTURE_FPS_LIMIT

    # ── Grace period ──────────────────────────────────────────────────────────
    print(f"[Proctor] Grace period: {STARTUP_GRACE_PERIOD}s...")
    grace_end  = time.time() + STARTUP_GRACE_PERIOD
    last_frame = 0.0

    while time.time() < grace_end:
        if _stop_event.is_set() or shared_state.get("terminate"):
            cap.release()
            return

        now = time.time()
        if now - last_frame >= frame_interval:
            ret, frame = cap.read()
            if ret:
                remaining = int(grace_end - now) + 1
                disp = frame.copy()
                cv2.putText(disp, f"Interview starting in {remaining}s...",
                            (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 220, 255), 2)
                try:
                    _display_queue.put_nowait(disp)
                except queue.Full:
                    pass
            last_frame = now
        else:
            time.sleep(0.01)

    print("[Proctor] Monitoring active.")
    with _annotation_lock:
        _annotation_state["status"] = "Monitoring..."

    # ── Main monitoring loop ──────────────────────────────────────────────────
    no_face_streak    = 0
    multi_face_streak = 0
    look_away_streak  = 0
    total_warnings    = 0
    last_tick         = time.time()
    last_frame        = 0.0

    try:
        while cap.isOpened():
            if _stop_event.is_set() or shared_state.get("terminate"):
                break

            now = time.time()

            if now - last_frame < frame_interval:
                time.sleep(0.005)
                continue

            ret, frame = cap.read()
            last_frame = time.time()
            if not ret:
                time.sleep(0.05)
                continue

            try:
                _display_queue.put_nowait(frame.copy())
            except queue.Full:
                pass

            if (now - last_tick) < CHECK_INTERVAL_SEC:
                continue
            last_tick = now

            frame_h, frame_w = frame.shape[:2]
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = _detect_faces(gray, cascade, frame_w)
            n     = len(faces)
            issued = None

            if n == 0:
                no_face_streak    += 1
                multi_face_streak  = 0
                look_away_streak   = 0
                status = f"No face ({no_face_streak}/{NO_FACE_WARN_AFTER})"
                if no_face_streak == NO_FACE_WARN_AFTER:
                    issued = "No face detected - please stay in frame"
                elif no_face_streak >= NO_FACE_TERM_AFTER:
                    issued = "Candidate absent - interview terminated"
                    shared_state["terminate"] = True

            elif n > 1:
                multi_face_streak += 1
                no_face_streak     = 0
                look_away_streak   = 0
                status = f"Multiple faces ({n})"
                if multi_face_streak == MULTI_FACE_WARN_AFTER:
                    issued = f"Multiple people detected ({n} faces)"
                elif multi_face_streak >= MULTI_FACE_TERM_AFTER:
                    issued = "Interview terminated - multiple people in frame"
                    shared_state["terminate"] = True

            else:
                no_face_streak    = 0
                multi_face_streak = 0
                direction = _gaze_direction(faces[0], frame_w, frame_h)
                if direction:
                    look_away_streak += 1
                    status = f"Looking {direction} ({look_away_streak}/{LOOK_AWAY_WARN_AFTER})"
                    if look_away_streak == LOOK_AWAY_WARN_AFTER:
                        issued = f"Please look at the screen (looking {direction})"
                    elif look_away_streak >= LOOK_AWAY_TERM_AFTER:
                        issued = "Interview terminated - prolonged inattention"
                        shared_state["terminate"] = True
                else:
                    look_away_streak = 0
                    status = "OK"

            with _annotation_lock:
                _annotation_state["faces"]         = faces
                _annotation_state["warning_count"] = total_warnings
                _annotation_state["status"]        = status

            if issued:
                total_warnings += 1
                print(f"[Proctor] Warning {total_warnings}: {issued}")
                shared_state["warning"] = issued
                with _annotation_lock:
                    _annotation_state["warning_count"] = total_warnings
                if total_warnings >= MAX_TOTAL_WARNINGS:
                    shared_state["terminate"] = True
                    print("[Proctor] Max warnings — terminating.")

    except Exception as e:
        print(f"[Proctor] Error: {e}")
    finally:
        cap.release()
        print("[Proctor] Camera released.")