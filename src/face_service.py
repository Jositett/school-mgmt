import os, pickle, datetime, pathlib, requests, base64, time, threading
import sqlite3
import cv2
import numpy as np
from datetime import datetime

# Import face_recognition with proper error handling
# Silence the import error by redirecting stderr
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

# Database setup
DB_PATH = "school.db"

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
            cls._instance.cleanup_invalid_encodings()  # Clean up any invalid encodings on startup
        return cls._instance

    # ---------- public API ----------
    def enrol_student(self, student_id: int, images_or_video: list[np.ndarray]) -> bool:
        """Pass either a list of cv2 images or a list with one video frame every 200 ms."""
        if not FACE_RECOGNITION_AVAILABLE or face_recognition is None:
            return False

        encodings = []
        for frame in images_or_video:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes = face_recognition.face_locations(rgb, model="hog")  # type: ignore # or "cnn" if GPU
            if boxes:
                encodings.append(face_recognition.face_encodings(rgb, boxes, model="small")[0])  # type: ignore - specify small model for 128-dim
        if len(encodings) < 1:
            return False
        mean_encoding = np.mean(encodings, axis=0)                   # simple average
        self._save_encoding(student_id, mean_encoding)
        self._load_encodings()                                       # refresh RAM
        return True

    def recognise(self, frame: np.ndarray) -> list[tuple[int, float]]:
        """Return [(student_id, distance), …] for all faces in frame (distance ≤ 0.45)."""
        if not FACE_RECOGNITION_AVAILABLE or face_recognition is None:
            return []

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(rgb, model="hog")  # type: ignore
        if not boxes:
            return []
        unknown_encodings = face_recognition.face_encodings(rgb, boxes, model="small")  # type: ignore - specify small model for 128-dim
        results = []
        for enc in unknown_encodings:
            if len(self.known_encodings) == 0:
                continue  # No known encodings to compare against

            # Ensure both encoding and known encodings are 1D and same size
            enc = np.array(enc, dtype=np.float32).flatten()  # Ensure 1D array

            # Validate encoding size (should be 128 for small model)
            if len(enc) != 128:
                print(f"Invalid encoding size: {len(enc)}, expected 128. Skipping.")
                continue

            # Filter known encodings to ensure they're valid 128-dim vectors
            valid_known_encodings = []
            valid_known_ids = []

            for i, known_enc in enumerate(self.known_encodings):
                known_enc_flat = np.array(known_enc, dtype=np.float32).flatten()
                if len(known_enc_flat) == 128:  # Valid size
                    valid_known_encodings.append(known_enc_flat)
                    valid_known_ids.append(self.known_ids[i])
                else:
                    print(f"Invalid stored encoding for student {self.known_ids[i]}: size {len(known_enc_flat)}")

            if not valid_known_encodings:
                continue  # No valid stored encodings

            try:
                # Convert to numpy array for consistent shape
                known_encodings_array = np.array(valid_known_encodings, dtype=np.float32)

                # Compute distances
                distances = face_recognition.face_distance(known_encodings_array, enc)  # type: ignore

                # Find best match
                best_idx = np.argmin(distances)
                if distances[best_idx] <= 0.45:  # tune threshold if needed
                    results.append((valid_known_ids[best_idx], float(distances[best_idx])))
            except ValueError as ve:
                print(f"Face recognition error during distance calculation: {ve} - skipping comparison")

        return results

    # ---------- internal ----------
    def _load_encodings(self):
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT student_id, encoding FROM face_encodings").fetchall()
        conn.close()
        self.known_ids = [r[0] for r in rows]
        self.known_encodings = [np.frombuffer(r[1], dtype=np.float32) for r in rows]

    def _save_encoding(self, student_id: int, enc: np.ndarray):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO face_encodings(student_id, encoding, updated_at) VALUES (?,?,?)",
            (student_id, enc.tobytes(), datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def cleanup_invalid_encodings(self):
        """Remove or fix invalid encodings in the database."""
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT student_id, encoding FROM face_encodings").fetchall()

        invalid_count = 0
        for student_id, encoding_bytes in rows:
            try:
                enc = np.frombuffer(encoding_bytes, dtype=np.float32)
                if len(enc) != 128:
                    print(f"Cleaning up invalid encoding for student {student_id}: {len(enc)} dimensions")
                    # Delete invalid encoding - user will need to re-enroll
                    conn.execute("DELETE FROM face_encodings WHERE student_id = ?", (student_id,))
                    invalid_count += 1
            except Exception as e:
                print(f"Error processing encoding for student {student_id}: {e}")
                conn.execute("DELETE FROM face_encodings WHERE student_id = ?", (student_id,))
                invalid_count += 1

        if invalid_count > 0:
            conn.commit()
            print(f"Cleaned up {invalid_count} invalid face encodings")
            # Refresh in-memory cache
            self._load_encodings()

        conn.close()
