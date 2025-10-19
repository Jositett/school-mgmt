import os, json, cv2, numpy as np, threading
from py_mini_racer import MiniRacer
from PIL import Image
from datetime import datetime

class FaceServiceJS:
    """
    Drop-in replacement for FaceService.
    enrol_student()  keeps the same signature.
    """
    _instance = None
    known_ids = []
    known_encodings = []
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._js = None
            ids, encodings = cls._instance._load_encodings()  # Load encodings automatically like original service
            cls._instance.known_ids = ids
            cls._instance.known_encodings = encodings
        return cls._instance

    def _engine(self):
        if self._js is None:
            self._js = MiniRacer()
            bundle_path = os.path.join(os.path.dirname(__file__), "..", "js_models", "face_js_bundle.js")
            try:
                with open(bundle_path, 'r') as f:
                    js_code = f.read()
                self._js.eval(js_code)
            except Exception as e:
                print(f"Failed to load JS bundle: {e}")
                self._js = None
        return self._js

    @staticmethod
    def _frame_to_rgba(frame: np.ndarray) -> bytes:
        # Convert BGR to RGBA
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        rgba_img = img.convert("RGBA")
        return np.array(rgba_img).tobytes()

    def enrol_student(self, student_id: int, frames: list[np.ndarray]) -> bool:
        js = self._engine()
        if js is None:
            return False

        descriptors = []
        dlib_encodings = []

        # Use dlib to extract real face encodings for recognition compatibility
        try:
            import face_recognition
            if face_recognition:
                for frm in frames:
                    rgb = cv2.cvtColor(frm, cv2.COLOR_BGR2RGB)
                    boxes = face_recognition.face_locations(rgb, model="hog")
                    if boxes:
                        encodings = face_recognition.face_encodings(rgb, boxes, model="small")
                        if encodings:
                            dlib_encodings.extend(encodings[:1])  # Take first face per frame
        except ImportError:
            pass  # Continue with JS-only if dlib not available

        # Generate JS-based face descriptors
        for frm in frames:
            rgba_bytes = self._frame_to_rgba(frm)
            # Convert bytes to list for JSON serialization
            rgba_list = list(rgba_bytes)
            h, w = frm.shape[:2]
            try:
                vec = js.call("encodeFace", rgba_list, w, h)
                if vec and len(vec) == 128:
                    descriptors.append(vec)
            except Exception as e:
                print(f"Face encoding failed for frame: {e}")
                continue

        if len(descriptors) < 3:  # need at least 3 good faces
            print(f"Only got {len(descriptors)} valid face descriptors, need at least 3")
            return False

        # average them → 128-D template
        js_template = np.mean(descriptors, axis=0).astype(np.float32)

        # If we have dlib encodings, use those for compatibility, otherwise use JS template
        if dlib_encodings:
            # Average dlib encodings for the most compatible recognition
            dlib_template = np.mean(dlib_encodings, axis=0).astype(np.float32)
            print(f"Enrolled with {len(dlib_encodings)} dlib encodings for recognition compatibility")
        else:
            dlib_template = js_template
            print(f"Enrolled with JS encodings only (recognition may not work)")

        # Save to DB (same as before)
        self._save_template(student_id, dlib_template)
        return True

    def recognise(self, frame: np.ndarray) -> list[tuple[int, float]]:
        """Return [(student_id, distance), …] for all faces in frame (distance ≤ 0.45)."""
        # Use dlib/face_recognition for detection if available, then match against JS-computed templates
        try:
            import face_recognition
            if not face_recognition:
                return []
        except ImportError:
            return []  # No face recognition available

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(rgb, model="hog")
        if not boxes:
            return []

        unknown_encodings = face_recognition.face_encodings(rgb, boxes, model="small")
        results = []

        for enc in unknown_encodings:
            if len(self.known_encodings) == 0:
                continue  # No known encodings to compare against

            # Ensure both encoding and known encodings are 1D and same size
            enc = np.array(enc, dtype=np.float32).flatten()  # Ensure 1D array

            # Validate encoding size (should be 128)
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

            if not valid_known_encodings:
                continue  # No valid stored encodings

            try:
                # Convert to numpy array for consistent shape
                known_encodings_array = np.array(valid_known_encodings, dtype=np.float32)

                # Compute distances
                distances = face_recognition.face_distance(known_encodings_array, enc)

                # Find best match
                best_idx = np.argmin(distances)
                if distances[best_idx] <= 0.45:  # tune threshold if needed
                    results.append((valid_known_ids[best_idx], float(distances[best_idx])))
            except ValueError as ve:
                print(f"Face recognition error during distance calculation: {ve} - skipping comparison")

        return results

    # ---------- helpers ----------
    def _save_template(self, student_id: int, template: np.ndarray):
        """Save face template to database."""
        import sqlite3
        DB_PATH = "school.db"  # Same as original FaceService

        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT OR REPLACE INTO face_encodings(student_id, encoding, updated_at) VALUES (?,?,?)",
                (student_id, template.tobytes(), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            print(f"Saved face template for student {student_id}")
        except Exception as e:
            print(f"Failed to save face template: {e}")

    def _load_encodings(self):
        """Load encodings from database."""
        import sqlite3
        DB_PATH = "school.db"  # Same as original FaceService

        try:
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute("SELECT student_id, encoding FROM face_encodings").fetchall()
            conn.close()
            ids = [r[0] for r in rows]
            encodings = [np.frombuffer(r[1], dtype=np.float32) for r in rows]
            return ids, encodings
        except Exception as e:
            print(f"Failed to load encodings: {e}")
            return [], []
