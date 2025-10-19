import flet as ft
import cv2
import base64
import time
from database import get_all_students
import threading
import numpy as np
import os
from datetime import date

# Use the fast JS-based face service (no dlib dependency)
from face_service_js import FaceServiceJS as FaceService
print("Using fast OpenCV+JavaScript face recognition (no dlib dependency)")

# Thread-safe resources
camera_lock = threading.Lock()
enrollment_in_progress = threading.Event()

# Thread control for preview
preview_thread = None
stop_preview = threading.Event()

# Import face_recognition safely
import sys
old_stderr = sys.stderr
with open(os.devnull, 'w') as devnull:
    sys.stderr = devnull
    try:
        import face_recognition
        FACE_AVAILABLE = True
    except ImportError:
        FACE_AVAILABLE = False
        face_recognition = None
sys.stderr = old_stderr

# 1×1 transparent PNG base64 (valid, tiny)
PLACEHOLDER_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def create_enrol_face_view(page: ft.Page, show_snackbar):
    """Create modern responsive face enrollment view."""

    # Get responsive dimensions
    window_width = getattr(page.window, 'width', 1200)
    window_height = getattr(page.window, 'height', 800)

    # Calculate responsive sizes
    is_mobile = window_width < 768

    # Camera display dimensions
    if is_mobile:
        camera_width = min(window_width - 40, 400)  # Max 400px on mobile
        camera_height = int(camera_width * 0.75)  # 4:3 aspect ratio
    else:
        camera_width = min(window_width - 400, 640)  # Leave space for sidebar
        camera_height = 480

    student_dropdown = ft.Dropdown(
        label="Select Student",
        hint_text="Choose student to enrol face",
        width=400 if not is_mobile else None,
        expand=is_mobile,
    )

    # Camera selection dropdown - dynamically populated
    camera_dropdown = ft.Dropdown(
        label="Select Camera",
        hint_text="Choose camera device",
        width=200 if not is_mobile else None,
        value="0",
        expand=is_mobile,
    )

    # Live enrollment status indicator - status dot and text
    status_dot = ft.Container(
        width=12,
        height=12,
        border_radius=6,
        bgcolor=ft.Colors.GREY_400,
    )
    status_text_display = ft.Text("Ready", size=14, color=ft.Colors.GREY_600)

    status_indicator = ft.Container(
        content=ft.Row([
            status_dot,
            status_text_display,
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=15, vertical=8),
        border_radius=20,
        bgcolor=ft.Colors.GREY_100,
    )

    # Camera preview and indicators
    camera_preview = ft.Image(
        src_base64=PLACEHOLDER_B64,   # ← never empty
        width=camera_width,
        height=camera_height,
        fit=ft.ImageFit.CONTAIN,
        border_radius=15,
    )
    camera_status = ft.Text("Camera Status: Not started", size=12, color=ft.Colors.GREY_600)

    # Lighting indicator row
    lighting_indicator_row = ft.Row([
        ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, color=ft.Colors.ORANGE_500),
        ft.Text("Lighting: Unknown", size=12, color=ft.Colors.ORANGE_500)
    ])
    lighting_indicator = ft.Container(
        content=lighting_indicator_row,
        visible=False
    )

    # Face indicator components
    face_icon = ft.Icon(ft.Icons.FACE, color=ft.Colors.RED_500)
    face_text = ft.Text("Face: Not detected", size=12, color=ft.Colors.RED_500)
    face_indicator_row = ft.Row([face_icon, face_text])
    face_indicator = ft.Container(
        content=face_indicator_row,
        visible=False
    )
    status_text = ft.Text("", size=14)

    # Now define the actual implementations
    def test_enrollment():
        """Quick test to verify enrollment components work"""
        print("=== Testing Face Enrollment ===")

        # Test 1: Check if students are loaded
        students = get_all_students()
        print(f"Students found: {len(students)}")

        # Test 2: Check camera access
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("Camera 0 accessible")
            ret, frame = cap.read()
            if ret:
                print("Can read frames from camera")
            else:
                print("Cannot read frames from camera")
            cap.release()
        else:
            print("Camera 0 not accessible")

        # Test 3: Check FaceService
        try:
            face_service = FaceService()
            print("FaceService created successfully")
        except Exception as e:
            print(f"FaceService error: {e}")

    # Run this test when the view loads
    test_enrollment()

    def load_students():
        """Load students into dropdown."""
        students = get_all_students()
        print(f"Loaded {len(students)} students")  # Debug print
        student_dropdown.options = [
            ft.dropdown.Option(key=str(s.id), text=s.name) for s in students
        ]
        if students:
            student_dropdown.value = str(students[0].id)
            print(f"Selected student: {students[0].name}")  # Debug print

    def load_camera_devices():
        """Load available camera devices into dropdown."""
        available_cameras = []

        # Suppress OpenCV stderr during camera detection
        old_stderr = os.dup(2)  # Duplicate stderr file descriptor
        devnull = os.open(os.devnull, os.O_WRONLY)

        try:
            # Redirect stderr to /dev/null to suppress OpenCV errors
            os.dup2(devnull, 2)

            for i in range(10):  # Check first 10 camera indices
                try:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        available_cameras.append(i)
                        cap.release()
                except Exception:
                    pass
        finally:
            # Restore stderr
            os.dup2(old_stderr, 2)
            os.close(old_stderr)
            os.close(devnull)

        camera_dropdown.options = [
            ft.dropdown.Option(key=str(i), text=f"Camera {i}") for i in available_cameras
        ]

        # Select first available camera if none selected
        if available_cameras and not camera_dropdown.value:
            camera_dropdown.value = str(available_cameras[0])

    def update_camera_preview(frame, faces_detected=0):
        """Update camera preview with frame and face detection indicators."""
        async def update():
            if frame is not None:
                # Convert BGR to RGB and encode as base64 for Flet
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                success, encoded_img = cv2.imencode('.png', rgb_frame)
                if success:
                    img_base64 = base64.b64encode(encoded_img.tobytes()).decode('utf-8')
                    camera_preview.src_base64 = img_base64

            # Update indicators
            camera_status.value = "Camera Status: Active" if frame is not None else "Camera Status: Error"
            camera_status.color = ft.Colors.GREEN_600 if frame is not None else ft.Colors.RED_600

            if faces_detected > 0:
                face_text.value = f"Face: Detected ({faces_detected})"
                face_text.color = ft.Colors.GREEN_600
                face_icon.color = ft.Colors.GREEN_600
            else:
                face_text.value = "Face: Not detected"
                face_text.color = ft.Colors.RED_500
                face_icon.color = ft.Colors.RED_500

            # Show indicators
            lighting_indicator.visible = True
            face_indicator.visible = True

            page.update()

        page.run_task(update)

    def camera_preview_thread():
        """Thread to continuously update camera preview."""
        with camera_lock:
            selected_camera = int(camera_dropdown.value or 0)
            cap = cv2.VideoCapture(selected_camera)

            if not cap.isOpened():
                update_camera_preview(None, 0)
                return

            try:
                import face_recognition
            except ImportError:
                face_recognition = None

            try:
                while not stop_preview.is_set():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    faces_detected = 0
                    if face_recognition is not None:
                        try:
                            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                            faces_detected = len(face_locations)
                        except Exception:
                            pass

                    update_camera_preview(frame, faces_detected)
                    time.sleep(0.5)  # Update every 500ms
            finally:
                cap.release()

    def start_camera_preview():
        """Start camera preview thread."""
        global preview_thread
        # Stop existing preview if running
        if preview_thread and preview_thread.is_alive():
            stop_preview.set()
            preview_thread.join(timeout=1.0)  # Wait up to 1 second for thread to stop

        # Reset stop signal and start new preview
        stop_preview.clear()
        camera_status.value = "Camera Status: Starting..."
        camera_status.color = ft.Colors.ORANGE_500
        page.update()

        preview_thread = threading.Thread(target=camera_preview_thread, daemon=True)
        preview_thread.start()

    def enrol_student_face():
        """Enrol student face using webcam with clear user guidance."""
        print("Enroll button clicked!")  # Debug print
        if enrollment_in_progress.is_set():
            show_snackbar("Enrollment already in progress!", True)
            return

        if not student_dropdown.value:
            show_snackbar("Please select a student!", True)
            return

        # Force stop any camera preview before starting enrollment
        global preview_thread
        if preview_thread and preview_thread.is_alive():
            print("Forcing stop of existing preview thread...")  # Debug print
            stop_preview.set()
            # Give it a moment to stop
            preview_thread.join(timeout=2.0)
            if preview_thread.is_alive():
                print("Warning: Preview thread did not stop gracefully")  # Debug print
            else:
                print("Preview thread stopped successfully")  # Debug print

        # Reset the stop flag for future use
        stop_preview.clear()

        print("Starting enrollment...")  # Debug print
        # Start enrollment in a background thread to avoid blocking the UI
        enrollment_in_progress.set()
        threading.Thread(target=_do_enrollment, daemon=True).start()

    def _do_enrollment():
        """Background enrollment function that handles all blocking operations."""
        try:
            print("Enrollment thread started")  # Debug print

            # Try to acquire camera lock with timeout, then fall back to stopping preview
            lock_acquired = camera_lock.acquire(timeout=3.0)  # Wait max 3 seconds

            if not lock_acquired:
                print("Could not acquire camera lock, trying to stop preview thread...")  # Debug print
                # Try one more time to stop preview if running
                global preview_thread
                if preview_thread and preview_thread.is_alive():
                    stop_preview.set()
                    preview_thread.join(timeout=1.0)

                # Now try to get the lock again
                lock_acquired = camera_lock.acquire(timeout=2.0)
            if not lock_acquired:
                print("Failed to acquire camera lock after stopping preview")  # Debug print
                raise Exception("Cannot access camera - another process may be using it")

            print("Camera lock acquired successfully")  # Debug print

            # Get student ID from dropdown
            assert student_dropdown.value is not None
            student_id = int(student_dropdown.value)

            # Update UI for starting
            def update_ui(message, dot_color, text_color, status_value):
                async def _update():
                    status_text.value = message
                    status_dot.bgcolor = dot_color
                    status_text_display.value = status_value
                    status_text_display.color = text_color
                    page.update()
                page.run_task(_update)

            update_ui("⚠️ Get ready! Look directly at the camera with your face fully visible.",
                      ft.Colors.ORANGE_500, ft.Colors.ORANGE_700, "Starting")

            # Pause for 2 seconds to let user prepare
            time.sleep(2)

            update_ui("🔴 Recording... KEEP FACE STEADY: 3",
                      ft.Colors.RED_500, ft.Colors.RED_700, "Recording")
            time.sleep(1)

            update_ui("🔴 Recording... KEEP FACE STEADY: 2",
                      ft.Colors.RED_500, ft.Colors.RED_700, "Recording")
            time.sleep(1)

            update_ui("🔴 Recording... KEEP FACE STEADY: 1",
                      ft.Colors.RED_500, ft.Colors.RED_700, "Recording")
            time.sleep(1)

            update_ui("📷 Recording... Keep your face steady and visible!",
                      ft.Colors.RED_500, ft.Colors.RED_700, "Recording")

            try:
                # Add this check
                if not camera_dropdown.value:
                    update_ui("❌ No camera selected!", ft.Colors.RED_500, ft.Colors.RED_700, "Camera Error")
                    show_snackbar("No camera selected!", True)
                    return

                selected_camera = int(camera_dropdown.value)
                print(f"Attempting to access camera {selected_camera}")  # Debug print
                cap = cv2.VideoCapture(selected_camera)

                if not cap.isOpened():
                    print(f"Failed to open camera {selected_camera}")  # Debug print
                    update_ui(f"❌ Cannot access camera {selected_camera}. Check camera permissions and hardware.",
                             ft.Colors.RED_500, ft.Colors.RED_700, "Camera Error")
                    show_snackbar(f"Cannot access camera {selected_camera}!", True)
                    return

                frames = []
                faces_detected = 0
                frame_count = 0
                start_time = time.time()

                # Capture frames with real-time feedback and clear instructions
                while len(frames) < 15 and (time.time() - start_time) < 8:  # Extended to 8 seconds
                    ret, frame = cap.read()
                    if not ret:
                        continue

                    frame_count += 1
                    remaining_seconds = int(8 - (time.time() - start_time))

                    # Check for faces
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    current_faces = 0
                    if FACE_AVAILABLE and face_recognition:
                        try:
                            face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                            current_faces = len(face_locations)
                        except Exception:
                            pass

                    # Always capture frames if face recognition is disabled
                    # Only capture face frames if face recognition is enabled
                    should_capture = True
                    if FACE_AVAILABLE and face_recognition and current_faces == 0:
                        should_capture = False

                    if should_capture:
                        frames.append(frame.copy())
                        faces_detected = max(faces_detected, current_faces)

                    # Update progress message with clear instructions
                    captured_frames = len(frames)
                    progress_text = ""

                    if captured_frames < 5:
                        progress_text = f"⏳ Getting frames... {captured_frames}/15 ({remaining_seconds}s left) - Keep face steady!"

                        if current_faces == 0 and FACE_AVAILABLE:
                            progress_text += " FACE NOT DETECTED!"

                    elif captured_frames < 10:
                        progress_text = f"🟡 Good progress... {captured_frames}/15 ({remaining_seconds}s left) - Keep face steady!"

                    elif captured_frames < 15:
                        progress_text = f"🟢 Almost done... {captured_frames}/15 ({remaining_seconds}s left) - Keep face steady!"

                    else:
                        progress_text = "✅ Capture complete! Processing..."

                    status_text.value = progress_text
                    page.update()
                    time.sleep(0.3)  # 300ms intervals for better capture rate

                cap.release()

                if len(frames) < 5:
                    update_ui("❌ Not enough frames captured! Try again - keep face steady in camera view during countdown.",
                             ft.Colors.RED_500, ft.Colors.RED_700, "Failed")
                    show_snackbar("Face enrolment failed! Keep face steady during recording.", True)
                else:
                    update_ui("🔄 Processing captured frames...",
                             ft.Colors.BLUE_600, ft.Colors.BLUE_600, "Processing")
                    page.update()

                    # Check if FaceService is available
                    try:
                        print("Initializing FaceService...")  # Debug print
                        face_service = FaceService()
                        print("FaceService initialized successfully")  # Debug print

                        print(f"Enrolling student ID {student_id} with {len(frames)} frames")  # Debug print
                        if face_service.enrol_student(student_id, frames):
                            print("Face enrollment successful")  # Debug print
                            update_ui(f"✅ Success! Face enrolled using {len(frames)} frames.",
                                     ft.Colors.GREEN_500, ft.Colors.GREEN_700, "Success")
                            show_snackbar("Face enrolled successfully! 🎉")
                        else:
                            print("Face enrollment failed - no face detected")  # Debug print
                            update_ui("❌ No face detected in captured frames. Try again with better lighting and clear face view.",
                                     ft.Colors.RED_500, ft.Colors.RED_700, "No Face")
                            show_snackbar("No face detected! Ensure good lighting and clear face view.", True)
                    except Exception as service_ex:
                        print(f"FaceService error: {str(service_ex)}")  # Debug print
                        update_ui(f"❌ Face recognition service error: {str(service_ex)}",
                                 ft.Colors.RED_500, ft.Colors.RED_700, "Error")
                        show_snackbar("Face recognition service error!", True)
            except Exception as ex:
                update_ui(f"❌ Camera operation failed: {str(ex)}",
                         ft.Colors.RED_500, ft.Colors.RED_700, "Error")
                show_snackbar("Camera operation failed!", True)
        except Exception as thread_ex:
            print(f"Enrollment thread error: {thread_ex}")
            show_snackbar("Enrollment failed due to unexpected error!", True)
        finally:
            camera_lock.release()
            enrollment_in_progress.clear()

    # Create buttons now that functions are defined
    capture_btn = ft.ElevatedButton(
        "Start Webcam Enrollment",
        icon=ft.Icons.VIDEOCAM,
        height=50,
        width=180 if not is_mobile else None,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
        ),
        on_click=lambda e: (print("Button clicked!"), enrol_student_face())[1],  # Debug print
    )

    start_preview_btn = ft.ElevatedButton(
        "Start Camera Preview",
        icon=ft.Icons.VIDEOCAM_OUTLINED,
        height=50,
        width=180 if not is_mobile else None,
        on_click=lambda e: start_camera_preview(),
    )

    load_students()
    load_camera_devices()

    # Create responsive layout
    if is_mobile:
        # Mobile layout - stacked vertically
        return ft.Container(
            content=ft.Column([
                # Header with status indicator
                ft.Container(
                    content=ft.Row([
                        ft.Text("📷 Face Enrollment", size=20, weight=ft.FontWeight.BOLD),
                        status_indicator,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.symmetric(vertical=20, horizontal=10),
                ),

                # Student and camera selection
                ft.Container(
                    content=ft.Column([
                        student_dropdown,
                        ft.Container(height=10),
                        camera_dropdown,
                    ], spacing=10),
                    padding=ft.padding.symmetric(vertical=10, horizontal=20),
                ),

                # Preview button and camera display
                ft.Container(
                    content=ft.Column([
                        start_preview_btn,
                        ft.Container(height=10),
                        ft.Container(
                            content=camera_preview,
                            alignment=ft.alignment.center,
                            bgcolor=ft.Colors.BLACK,
                            height=camera_height + 20,
                            border_radius=20,
                        ),
                    ], spacing=10),
                    padding=ft.padding.symmetric(horizontal=20),
                ),

                # Indicators
                ft.Container(
                    content=ft.Column([
                        camera_status,
                        lighting_indicator,
                        face_indicator,
                    ], spacing=5),
                    margin=ft.margin.symmetric(horizontal=20, vertical=10),
                ),

                # Capture controls
                ft.Container(
                    content=ft.Column([
                        capture_btn,
                        ft.Container(height=10),
                        ft.Container(
                            content=status_text,
                            alignment=ft.alignment.center,
                            padding=ft.padding.symmetric(vertical=10),
                        ),
                    ], spacing=10),
                    padding=ft.padding.symmetric(horizontal=20, vertical=10),
                ),

                # Instructions card
                ft.Container(
                    content=ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE_600),
                                    ft.Text("Enrollment Tips", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600),
                                ], spacing=8),
                                ft.Text("• Ensure bright, even lighting", size=12),
                                ft.Text("• Position face clearly in camera", size=12),
                                ft.Text("• Keep face steady during capture", size=12),
                                ft.Text("• 15 frames needed for enrollment", size=12),
                                ft.Text("• Preview and capture separately", size=12, color=ft.Colors.GREY_700),
                            ], spacing=5),
                            padding=15,
                        ),
                        elevation=2,
                    ),
                    margin=ft.margin.symmetric(horizontal=20, vertical=20),
                ),
            ], spacing=0, tight=True),
            expand=True,
            bgcolor=ft.Colors.SURFACE,
        )
    else:
        # Desktop layout - side by side with sidebar
        return ft.Container(
            content=ft.Row([
                # Main camera area
                ft.Container(
                    content=ft.Column([
                        # Header
                        ft.Container(
                            content=ft.Row([
                                ft.Text("📷 Face Enrollment", size=24, weight=ft.FontWeight.BOLD),
                                status_indicator,
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=ft.padding.symmetric(vertical=20, horizontal=20),
                        ),

                        # Student and camera selection
                        ft.Container(
                            content=ft.Row([
                                student_dropdown,
                                camera_dropdown,
                            ], spacing=20),
                            padding=ft.padding.symmetric(horizontal=20),
                        ),

                        # Camera display and controls
                        ft.Container(
                            content=ft.Column([
                                ft.Container(
                                    content=start_preview_btn,
                                    alignment=ft.alignment.center,
                                    padding=ft.padding.symmetric(vertical=10),
                                ),
                                ft.Container(
                                    content=ft.Container(
                                        content=camera_preview,
                                        alignment=ft.alignment.center,
                                        bgcolor=ft.Colors.BLACK,
                                        height=camera_height + 40,
                                        border_radius=20,
                                    ),
                                    alignment=ft.alignment.center,
                                    margin=ft.margin.symmetric(horizontal=20),
                                ),
                            ], spacing=15),
                        ),

                        # Indicators and capture
                        ft.Container(
                            content=ft.Column([
                                ft.Container(
                                    content=ft.Row([
                                        camera_status,
                                        lighting_indicator,
                                        face_indicator,
                                    ], spacing=20),
                                    alignment=ft.alignment.center,
                                    padding=ft.padding.symmetric(vertical=10),
                                ),
                                ft.Container(
                                    content=capture_btn,
                                    alignment=ft.alignment.center,
                                    padding=ft.padding.symmetric(vertical=10),
                                ),
                                ft.Container(
                                    content=status_text,
                                    alignment=ft.alignment.center,
                                    padding=ft.padding.symmetric(vertical=10),
                                ),
                            ], spacing=15),
                            margin=ft.margin.symmetric(horizontal=20, vertical=20),
                        ),
                    ], spacing=0),
                    expand=True,
                ),

                # Sidebar with instructions
                ft.VerticalDivider(width=1),
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Text("📋 Enrollment Guide", size=18, weight=ft.FontWeight.BOLD),
                            padding=ft.padding.all(20),
                        ),

                        # Instructions card
                        ft.Container(
                            content=ft.Card(
                                content=ft.Container(
                                    content=ft.Column([
                                        ft.Row([
                                            ft.Icon(ft.Icons.CAMERA_ALT, color=ft.Colors.BLUE_600),
                                            ft.Text("Step-by-Step Guide", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600),
                                        ], spacing=8),
                                        ft.Text("1. Select a student from the dropdown", size=12),
                                        ft.Text("2. Choose your camera device", size=12),
                                        ft.Text("3. Click 'Start Camera Preview' to test", size=12),
                                        ft.Text("4. When ready, click 'Start Enrollment'", size=12),
                                        ft.Text("5. Keep face in view during capture", size=12),
                                        ft.Divider(height=15),
                                        ft.Text("Tips:", size=12, weight=ft.FontWeight.BOLD),
                                        ft.Text("• Bright, even lighting works best", size=12),
                                        ft.Text("• Face camera directly", size=12),
                                        ft.Text("• Avoid hats, sunglasses", size=12),
                                        ft.Text("• 15 frames = ~3 seconds", size=12, color=ft.Colors.GREY_700),
                                    ], spacing=8),
                                    padding=15,
                                ),
                                elevation=2,
                            ),
                            margin=ft.margin.symmetric(horizontal=15),
                        ),

                        # Status info
                        ft.Container(
                            content=ft.Card(
                                content=ft.Container(
                                    content=ft.Column([
                                        ft.Row([
                                            ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.GREEN_600),
                                            ft.Text("Status Information", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_600),
                                        ], spacing=8),
                                        ft.Text("🟢 Green: Everything working", size=12),
                                        ft.Text("🟡 Orange: Processing", size=12),
                                        ft.Text("🔴 Red: Error occurred", size=12),
                                        ft.Divider(height=10),
                                        ft.Text("Enrollment creates a face encoding from 15 frames for reliable recognition.", size=12, color=ft.Colors.GREY_700),
                                    ], spacing=8),
                                    padding=15,
                                ),
                                elevation=2,
                            ),
                            margin=ft.margin.all(15),
                            expand=True,
                        ),
                    ], spacing=0),
                    width=350,
                    bgcolor=ft.Colors.SURFACE,
                ),
            ], spacing=0),
            expand=True,
        )
