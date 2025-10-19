import os, json, cv2, numpy as np, threading
from py_mini_racer import MiniRacer
from PIL import Image
from datetime import datetime

class FaceServiceJS:
    """
    Drop-in replacement for FaceService.
    Uses OpenCV Haar cascades + JS encoding - no dlib dependencies.
    enrol_student() keeps the same signature.
    """
    _instances = {}
    _known_data_lock = threading.Lock()

    # Declare instance attributes for better IDE support
    _js = None  # MiniRacer or None
    face_cascade = None
    known_ids = []
    known_encodings = []

    def __new__(cls):
        # Return thread-local instances since PyMiniRacer is not thread-safe
        thread_id = threading.current_thread().ident
        if thread_id not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[thread_id] = instance

            # Initialize instance attributes
            instance._js = None
            instance.face_cascade = None
            instance._load_face_detector()

            # Load known encodings (shared across threads, but each instance caches them)
            with cls._known_data_lock:
                ids, encodings = instance._load_encodings()
                instance.known_ids = ids
                instance.known_encodings = encodings

        return cls._instances[thread_id]

    def _load_face_detector(self):
        """Load OpenCV Haar cascade for fast face detection."""
        try:
            # Try to find the cascade file in common locations
            cascade_paths = [
                os.path.join(os.path.dirname(__file__), "..", "haarcascade_frontalface_default.xml"),
                "haarcascade_frontalface_default.xml",
                os.path.join(os.path.dirname(__file__), "..", "models", "haarcascade_frontalface_default.xml"),
            ]

            for cascade_path in cascade_paths:
                if os.path.exists(cascade_path):
                    self.face_cascade = cv2.CascadeClassifier(cascade_path)
                    if not self.face_cascade.empty():
                        print(f"Loaded face cascade from: {cascade_path}")
                        return
                    else:
                        print(f"Failed to load cascade from: {cascade_path}")

            # If no cascade found, create a fallback simple detector
            print("No Haar cascade found, using fallback detector")
            self.face_cascade = None  # Will use JS-only detection

        except Exception as e:
            print(f"Face detector loading error: {e}")
            self.face_cascade = None

    def _engine(self):
        """Initialize JS engine for face encoding with comprehensive error handling."""
        if self._js is None:
            try:
                # Try to import MiniRacer if not already available
                import py_mini_racer
            except ImportError:
                print("PyMiniRacer not available. Install with: pip install py-mini-racer")
                return None

            try:
                self._js = MiniRacer()
                bundle_path = os.path.join(os.path.dirname(__file__), "..", "js_models", "face_js_bundle.js")

                if not os.path.exists(bundle_path):
                    print(f"JS bundle not found: {bundle_path}")
                    self._js = None
                    return None

                with open(bundle_path, 'r', encoding='utf-8') as f:
                    js_code = f.read()

                if not js_code.strip():
                    print("JS bundle is empty")
                    self._js = None
                    return None

                # Execute the JS code
                self._js.eval(js_code)

                # Test if the main function is available by trying to call it
                try:
                    # Try to call the function with test data to ensure it works
                    test_result = self._js.call("encodeFace", [0, 0, 0, 255], 2, 2)
                    if not isinstance(test_result, list) or len(test_result) != 128:
                        print(f"encodeFace function test failed - returned {test_result}")
                        self._js = None
                        return None
                    print("encodeFace function successfully loaded and tested")
                except Exception as test_error:
                    print(f"encodeFace function test failed: {test_error}")
                    self._js = None
                    return None

                print("JavaScript face encoding engine initialized successfully")

            except UnicodeDecodeError as ue:
                print(f"JS bundle encoding error: {ue}")
                self._js = None
            except Exception as e:
                print(f"Failed to initialize JS engine: {e}")
                print("This may be due to missing dependencies or V8 compatibility issues")
                self._js = None

        return self._js

    @staticmethod
    def _frame_to_rgba(frame: np.ndarray) -> bytes:
        """Convert BGR frame to RGBA bytes for JS processing."""
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        rgba_img = img.convert("RGBA")
        return np.array(rgba_img).tobytes()

    def enrol_student(self, student_id: int, frames: list[np.ndarray]) -> bool:
        """Enroll student face using OpenCV + JS - no dlib dependencies."""
        js = self._engine()
        if js is None:
            print("JavaScript engine not available")
            return False

        descriptors = []

        for frm in frames:
            # Detect faces using OpenCV Haar cascades or fallback detection
            faces_detected = self._detect_faces_opencv(frm)
            if not faces_detected:
                print("No faces detected in frame")
                continue

            # Crop the first detected face (assume frontal)
            face = self._crop_face(frm, faces_detected[0])

            # Generate JS descriptor from the cropped face
            rgba_bytes = self._frame_to_rgba(face)
            rgba_list = list(rgba_bytes)
            h, w = face.shape[:2]

            try:
                vec = js.call("encodeFace", rgba_list, w, h)
                if vec and len(vec) == 128:
                    # Check if descriptor is not all zeros (valid detection)
                    if np.any(vec):  # Not all zeros = valid encoding
                        descriptors.append(vec)
                    else:
                        print("Invalid face descriptor (all zeros)")
                else:
                    print(f"Invalid descriptor length: {len(vec) if vec else 'None'}")
            except Exception as e:
                print(f"Face encoding failed: {e}")
                continue

        if len(descriptors) < 3:  # Need at least 3 valid face encodings
            print(f"Only got {len(descriptors)} valid face descriptors, need at least 3")
            return False

        # Average the descriptors to create final 128D template
        template = np.mean(descriptors, axis=0).astype(np.float32)
        print(f"Enrolled student {student_id} with {len(descriptors)} face encodings")

        # Save template to database
        self._save_template(student_id, template)
        return True

    def recognise(self, frame: np.ndarray) -> list[tuple[int, float]]:
        """Return [(student_id, distance), …] for all faces in frame using OpenCV + JS."""
        js = self._engine()
        if js is None or len(self.known_encodings) == 0:
            return []

        # Detect faces using OpenCV Haar cascades
        faces_detected = self._detect_faces_opencv(frame)
        if not faces_detected:
            return []

        results = []

        # Process each detected face
        for face_rect in faces_detected:
            # Crop face region
            face_img = self._crop_face(frame, face_rect)

            # Generate encoding for this face
            rgba_bytes = self._frame_to_rgba(face_img)
            rgba_list = list(rgba_bytes)
            h, w = face_img.shape[:2]

            try:
                unknown_enc = js.call("encodeFace", rgba_list, w, h)

                if unknown_enc and len(unknown_enc) == 128 and np.any(unknown_enc):
                    # Convert to numpy array
                    unknown_enc_arr = np.array(unknown_enc, dtype=np.float32)

                    # Compare with all known encodings
                    distances = []
                    for known_enc in self.known_encodings:
                        known_enc_arr = np.array(known_enc, dtype=np.float32)
                        # Cosine distance (1 - cosine similarity)
                        cos_sim = np.dot(unknown_enc_arr, known_enc_arr) / (
                            np.linalg.norm(unknown_enc_arr) * np.linalg.norm(known_enc_arr)
                        )
                        distance = 1.0 - cos_sim
                        distances.append(distance)

                    if distances:
                        best_idx = np.argmin(distances)
                        best_distance = distances[best_idx]

                        # Threshold for matches (adjust based on testing)
                        if best_distance <= 0.45:
                            results.append((self.known_ids[best_idx], float(best_distance)))

            except Exception as e:
                print(f"Face recognition error: {e}")
                continue

        return results

    def _detect_faces_opencv(self, frame: np.ndarray) -> list:
        """Detect faces using OpenCV Haar cascades."""
        if self.face_cascade is not None and not self.face_cascade.empty():
            try:
                # Convert to grayscale for Haar cascade detection
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Detect faces using Haar cascades
                faces = self.face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30),
                    maxSize=(300, 300)
                )

                # Return list of face rectangles [x, y, w, h]
                return [list(face) for face in faces] if len(faces) > 0 else []
            except Exception as e:
                print(f"OpenCV face detection error: {e}")

        # Fallback simple detection using JS (implemented in face_js_bundle.js)
        print("Using fallback face detection (JS-based)")
        js = self._engine()
        if js is not None:
            try:
                rgba_bytes = self._frame_to_rgba(frame)
                rgba_list = list(rgba_bytes)
                h, w = frame.shape[:2]
                faces = js.call("detectFacesSimple", rgba_list, w, h)
                return faces if faces else []
            except Exception as e:
                print(f"JS face detection error: {e}")

        return []

    def _crop_face(self, frame: np.ndarray, face_rect) -> np.ndarray:
        """Crop face region from frame."""
        try:
            x, y, w, h = face_rect
            # Add some padding around the face
            padding = int(min(w, h) * 0.2)  # 20% padding

            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(frame.shape[1], x + w + padding)
            y2 = min(frame.shape[0], y + h + padding)

            return frame[y1:y2, x1:x2]
        except Exception as e:
            print(f"Face cropping error: {e}")
            return frame  # Return full frame as fallback

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
