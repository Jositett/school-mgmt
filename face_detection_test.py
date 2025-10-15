import cv2
import numpy as np
import sys

# Add the current directory to path for imports
sys.path.insert(0, '.')

# Test face detection specifically
def test_face_detection():
    print("Testing face detection...")

    # Capture a frame from camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open camera")
        return False

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("ERROR: Cannot read frame from camera")
        return False

    print(f"Frame captured: shape {frame.shape}")

    # Test face_recognition import and face detection
    try:
        import face_recognition
        print("face_recognition module imported successfully")

        # Convert to RGB (face_recognition expects RGB)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        print(f"Converted to RGB: shape {rgb_frame.shape}")

        # Detect faces using face_recognition
        print("Detecting faces with face_recognition...")
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        print(f"Found {len(face_locations)} faces using face_recognition")

        if face_locations:
            for i, (top, right, bottom, left) in enumerate(face_locations):
                print(f"  Face {i+1}: top={top}, right={right}, bottom={bottom}, left={left}")

            # Try to get face encodings
            print("Getting face encodings...")
            encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            print(f"Got {len(encodings)} face encodings")

            if encodings:
                print("Face detection and encoding successful!")
                return True
            else:
                print("ERROR: Face locations found but no encodings generated")
                return False
        else:
            print("ERROR: No faces detected in the frame")
            # Save the frame for manual inspection
            cv2.imwrite('debug_no_faces.png', frame)
            print("Saved frame to debug_no_faces.png for inspection")
            return False

    except ImportError as e:
        print(f"ERROR: face_recognition import failed: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Exception during face detection: {e}")
        # Save the frame for manual inspection
        cv2.imwrite('debug_face_error.png', frame)
        print("Saved frame to debug_face_error.png for inspection")
        return False

if __name__ == "__main__":
    success = test_face_detection()
    sys.exit(0 if success else 1)