import cv2
import sys

def test_camera():
    print("Testing camera access...")
    cap = cv2.VideoCapture(0)  # Try default camera (index 0)

    if not cap.isOpened():
        print("ERROR: Cannot open camera")
        return False

    print("Camera opened successfully")

    # Read a single frame
    ret, frame = cap.read()
    if not ret:
        print("ERROR: Cannot read frame from camera")
        cap.release()
        return False

    print(f"Frame captured successfully. Frame shape: {frame.shape}")

    # Release the camera
    cap.release()
    cv2.destroyAllWindows()

    print("Camera test completed successfully")
    return True

if __name__ == "__main__":
    success = test_camera()
    sys.exit(0 if success else 1)