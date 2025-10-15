import flet as ft
import cv2
import base64
import time
from database import get_all_students
import threading
import numpy as np
import os
from datetime import date
from face_service import FaceService

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

    capture_btn = ft.ElevatedButton(
        "Start Webcam Enrollment",
        icon=ft.Icons.VIDEOCAM,
        height=50,
        width=180 if not is_mobile else None,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
        ),
        on_click=lambda e: enrol_student_face(),
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

    start_preview_btn = ft.ElevatedButton(
        "Start Camera Preview",
        icon=ft.Icons.VIDEOCAM_OUTLINED,
        height=50,
        width=180 if not is_mobile else None,
        on_click=lambda e: start_camera_preview(),
    )

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

    def load_students():
        """Load students into dropdown."""
        students = get_all_students()
        student_dropdown.options = [
            ft.dropdown.Option(key=str(s.id), text=s.name) for s in students
        ]
        if students:
            student_dropdown.value = str(students[0].id)

    def load_camera_devices():
        """Load available camera devices into dropdown."""
        available_cameras = []
        for i in range(10):  # Check first 10 camera indices
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    available_cameras.append(i)
                    cap.release()
            except Exception:
                pass

        camera_dropdown.options = [
            ft.dropdown.Option(key=str(i), text=f"Camera {i}") for i in available_cameras
        ]

        # Select first available camera if none selected
        if available_cameras and not camera_dropdown.value:
            camera_dropdown.value = str(available_cameras[0])

    def update_camera_preview(frame, faces_detected=0):
        """Update camera preview with frame and face detection indicators."""
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

    def camera_preview_thread():
        """Thread to continuously update camera preview."""
        selected_camera = int(camera_dropdown.value or 0)
        cap = cv2.VideoCapture(selected_camera)

        if not cap.isOpened():
            update_camera_preview(None, 0)
            return

        try:
            import face_recognition
        except ImportError:
            face_recognition = None

        while True:
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

        cap.release()

    def start_camera_preview():
        """Start camera preview thread."""
        camera_status.value = "Camera Status: Starting..."
        camera_status.color = ft.Colors.ORANGE_500
        page.update()

        threading.Thread(target=camera_preview_thread, daemon=True).start()

    def enrol_student_face():
        """Enrol student face using webcam."""
        if not student_dropdown.value:
            show_snackbar("Please select a student!", True)
            return

        student_id = int(student_dropdown.value)
        status_text.value = "Capturing face data... Keep face in view."
        status_dot.bgcolor = ft.Colors.ORANGE_500
        status_text_display.value = "Capturing"
        status_text_display.color = ft.Colors.ORANGE_700
        page.update()

        try:
            selected_camera = int(camera_dropdown.value or 0)
            cap = cv2.VideoCapture(selected_camera)
            if not cap.isOpened():
                status_text.value = "Error: Cannot access camera. Check camera permissions and hardware."
                status_text_display.value = "Camera Error"
                status_dot.bgcolor = ft.Colors.RED_500
                status_text_display.color = ft.Colors.RED_700
                show_snackbar("Camera access failed!", True)
                page.update()
                return

            frames = []
            faces_detected = 0
            start_time = time.time()

            # Capture frames with real-time feedback
            while len(frames) < 15 and (time.time() - start_time) < 5:  # Max 5 seconds
                ret, frame = cap.read()
                if not ret:
                    break

                # Check for faces in real-time for feedback
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if FACE_AVAILABLE and face_recognition:
                    try:
                        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                        if len(face_locations) > 0:
                            faces_detected = len(face_locations)
                            frames.append(frame.copy())
                    except Exception:
                        pass
                else:
                    frames.append(frame.copy())

                status_text.value = f"Capturing... Frame {len(frames)}/15 (faces: {faces_detected})"
                time.sleep(0.2)  # 200ms intervals

            cap.release()

            if len(frames) < 5:
                status_text.value = "Error: Not enough frames captured. Camera may be busy or not responding."
                status_dot.bgcolor = ft.Colors.RED_500
                status_text_display.value = "Failed"
                status_text_display.color = ft.Colors.RED_700
                show_snackbar("Face enrolment failed!", True)
            else:
                # Check if FaceService is available
                try:
                    face_service = FaceService()
                    if face_service.enrol_student(student_id, frames):
                        status_text.value = f"Face enrolled successfully! Used {len(frames)} frames."
                        status_dot.bgcolor = ft.Colors.GREEN_500
                        status_text_display.value = "Success"
                        status_text_display.color = ft.Colors.GREEN_700
                        show_snackbar("Face enrolled successfully!")
                    else:
                        status_text.value = "Error: No face detected. Ensure good lighting and face is clearly visible."
                        status_dot.bgcolor = ft.Colors.RED_500
                        status_text_display.value = "No Face"
                        status_text_display.color = ft.Colors.RED_700
                        show_snackbar("Face enrolment failed!", True)
                except Exception as service_ex:
                    status_text.value = f"Error: Face recognition service failed - {str(service_ex)}"
                    status_dot.bgcolor = ft.Colors.RED_500
                    status_text_display.value = "Error"
                    status_text_display.color = ft.Colors.RED_700
                    show_snackbar("Face recognition service error!", True)

        except Exception as ex:
            status_text.value = f"Error: Camera operation failed - {str(ex)}"
            status_dot.bgcolor = ft.Colors.RED_500
            status_text_display.value = "Error"
            status_text_display.color = ft.Colors.RED_700
            show_snackbar("Camera operation failed!", True)

        page.update()

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
