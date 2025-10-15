import sys
import os
import cv2
import time
import numpy as np

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_all_students, init_db
from face_service import FaceService

def test_face_enrollment():
    """Test the face enrollment functionality."""
    print("Initializing face enrollment test...")

    # Initialize database
    init_db()

    # Get all students
    students = get_all_students()
    if not students:
        print("ERROR: No students found in database. Please add students first.")
        return False

    student_id = students[0].id
    print(f"Using student ID: {student_id} ({students[0].name})")

    # Initialize FaceService
    face_service = FaceService()
    print("Face service initialized")

    # Capture frames (similar to the actual implementation)
    print("Starting camera capture...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("ERROR: Cannot open camera for face enrollment")
        return False

    frames = []
    start_time = time.time()
    max_frames = 15
    max_time = 5  # seconds

    print(f"Capturing up to {max_frames} frames for {max_time} seconds...")

    while len(frames) < max_frames and (time.time() - start_time) < max_time:
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
            print(f"Captured frame {len(frames)}")
            time.sleep(0.2)  # 200ms intervals
        else:
            print("Failed to read frame from camera")
            break

    cap.release()
    print(f"Camera capture completed. Captured {len(frames)} frames")

    if len(frames) < 5:
        print(f"ERROR: Not enough frames captured ({len(frames)} < 5)")
        return False

    # Test face enrollment
    print("Testing face enrollment...")
    try:
        success = face_service.enrol_student(student_id, frames)
        if success:
            print("SUCCESS: Face enrollment completed successfully!")
            return True
        else:
            print("ERROR: Face enrollment failed - no face detected")
            return False
    except Exception as e:
        print(f"ERROR: Exception during face enrollment: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_face_enrollment()
    sys.exit(0 if success else 1)