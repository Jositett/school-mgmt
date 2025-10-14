"""
Face recognition service for School Management System
"""
import cv2
import numpy as np
import pathlib
import requests
import datetime

# Import face_recognition with proper error handling
import sys
from io import StringIO

old_stderr = sys.stderr  # Store original stderr
redirected_stderr = StringIO()
sys.stderr = redirected_stderr

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError as e:
    FACE_RECOGNITION_AVAILABLE = False
    print(f"Face recognition module not available: {e}")
    print("Face recognition features will be disabled.")
    # Create a mock face_recognition module to prevent errors
    face_recognition = None

sys.stderr = old_stderr  # Restore stderr

from database import get_db_connection

MODEL_DIR = pathlib.Path("models")
MODEL_DIR.mkdir(exist_ok=True)
LANDMARKS = MODEL_DIR / "shape_predictor_68_face_landmarks.dat"

# one-time download
if not LANDMARKS.exists():
    print("Downloading face landmark model …")
    url = "https://github.com/AKSHAYUBHAT/face_recognition/raw/master/models/shape_predictor_68_face_landmarks.dat"
    open(LANDMARKS,"wb").write(requests.get(url).content)


class FaceService:
    """Singleton that keeps one in-memory copy of all encodings."""
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_encodings()
        return cls._instance

    # ---------- public API ----------
    def enrol_student(self, student_id: int, images_or_video: list[cv2.Mat]) -> bool:
        """Pass either a list of cv2 images or a list with one video frame every 200 ms."""
        if not FACE_RECOGNITION_AVAILABLE or face_recognition is None:
            return False

        encodings = []
        for frame in images_or_video:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes = face_recognition.face_locations(rgb, model="hog")  # or "cnn" if GPU
            if boxes:
                encoding = face_recognition.face_encodings(rgb, boxes)[0]
                encodings.append(encoding)

        if len(encodings) < 1:
            return False
        mean_encoding = np.mean(encodings, axis=0)                   # simple average
        self._save_encoding(student_id, mean_encoding)
        self._load_encodings()                                       # refresh RAM
        return True

    def recognise(self, frame: cv2.Mat) -> list[tuple[int, float]]:
        """Return [(student_id, distance), …] for all faces in frame (distance ≤ 0.45)."""
        if not FACE_RECOGNITION_AVAILABLE or face_recognition is None:
            return []

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(rgb, model="hog")
        if not boxes:
            return []
        unknown_encodings = face_recognition.face_encodings(rgb, boxes)
        results = []
        for enc in unknown_encodings:
            distances = face_recognition.face_distance(self.known_encodings, enc)
            best_idx = np.argmin(distances)
            if distances[best_idx] <= 0.45:          # tune threshold if needed
                results.append((self.known_ids[best_idx], float(distances[best_idx])))
        return results

    # ---------- internal ----------
    def _load_encodings(self):
        conn = get_db_connection()
        rows = conn.execute("SELECT student_id, encoding FROM face_encodings").fetchall()
        conn.close()
        self.known_ids = [r[0] for r in rows]
        self.known_encodings = [np.frombuffer(r[1], dtype=np.float32) for r in rows]

    def _save_encoding(self, student_id: int, enc: np.ndarray):
        conn = get_db_connection()
        conn.execute(
            "INSERT OR REPLACE INTO face_encodings(student_id, encoding, updated_at) VALUES (?,?,?)",
            (student_id, enc.tobytes(), datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
