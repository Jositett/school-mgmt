import flet as ft
import cv2
import base64
import time
from database import get_all_students
import threading
import numpy as np
from face_service import FaceService


def create_enrol_face_view(page: ft.Page, show_snackbar):
    """Create face enrolment view."""
    student_dropdown = ft.Dropdown(
        label="Select Student",
        hint_text="Choose student to enrol face",
        width=400,
    )

    capture_btn = ft.ElevatedButton(
        "Start Webcam Enrolment",
        icon=ft.Icons.VIDEOCAM,
        on_click=lambda e: enrol_student_face(),
    )

    # Camera preview and indicators
    camera_preview = ft.Image(width=320, height=240, fit=ft.ImageFit.CONTAIN)
    camera_status = ft.Text("Camera Status: Not started", size=12, color=ft.Colors.GREY_600)
    lighting_indicator = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, color=ft.Colors.ORANGE_500),
            ft.Text("Lighting: Unknown", size=12, color=ft.Colors.ORANGE_500)
        ]),
        visible=False
    )
    face_indicator = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.FACE, color=ft.Colors.RED_500),
            ft.Text("Face: Not detected", size=12, color=ft.Colors.RED_500)
        ]),
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
            face_indicator.content.controls[1].value = f"Face: Detected ({faces_detected})"
            face_indicator.content.controls[1].color = ft.Colors.GREEN_600
            face_indicator.content.controls[0].color = ft.Colors.GREEN_600
        else:
            face_indicator.content.controls[1].value = "Face: Not detected"
            face_indicator.content.controls[1].color = ft.Colors.RED_500
            face_indicator.content.controls[0].color = ft.Colors.RED_500

        # Show indicators
        lighting_indicator.visible = True
        face_indicator.visible = True

        page.update()

    def camera_preview_thread():
        """Thread to continuously update camera preview."""
        cap = cv2.VideoCapture(0)
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
        status_text.value = "Starting webcam... Hold still and look at camera."
        page.update()

        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                status_text.value = "Error: Cannot access camera. Check camera permissions and hardware."
                show_snackbar("Camera access failed!", True)
                page.update()
                return

            frames = []
            start_time = time.time()

            while len(frames) < 15 and (time.time() - start_time) < 5:  # Max 5 seconds
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
                time.sleep(0.2)  # 200ms intervals

            cap.release()

            if len(frames) < 5:
                status_text.value = "Error: Not enough frames captured. Camera may be busy or not responding."
                show_snackbar("Face enrolment failed!", True)
            else:
                # Check if FaceService is available
                try:
                    face_service = FaceService()
                    if face_service.enrol_student(student_id, frames):
                        status_text.value = "Face enrolled successfully!"
                        show_snackbar("Face enrolled successfully!")
                    else:
                        status_text.value = "Error: No face detected. Ensure good lighting and face is clearly visible."
                        show_snackbar("Face enrolment failed!", True)
                except Exception as service_ex:
                    status_text.value = f"Error: Face recognition service failed - {str(service_ex)}"
                    show_snackbar("Face recognition service error!", True)

        except Exception as ex:
            status_text.value = f"Error: Camera operation failed - {str(ex)}"
            show_snackbar("Camera operation failed!", True)

        page.update()

    load_students()

    return ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Text("Face Enrollment", size=24, weight=ft.FontWeight.BOLD),
                padding=20,
            ),
            ft.Divider(height=1),
            ft.Container(
                content=ft.Column([
                    student_dropdown,
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        "Start Camera Preview",
                        icon=ft.Icons.VIDEOCAM_OUTLINED,
                        on_click=lambda e: start_camera_preview(),
                    ),
                    ft.Container(height=10),
                    camera_preview,
                    ft.Container(height=10),
                    camera_status,
                    lighting_indicator,
                    face_indicator,
                    ft.Container(height=20),
                    capture_btn,
                    ft.Container(height=20),
                    status_text,
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE_700),
                            ft.Text("• Make sure the webcam is working", size=12),
                            ft.Text("• Position face in center of frame", size=12),
                            ft.Text("• Ensure good lighting", size=12),
                            ft.Text("• Look directly at camera", size=12),
                        ], spacing=5),
                        padding=20,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=10,
                    ),
                ], spacing=15),
                padding=20,
            ),
        ], spacing=0, expand=True),
        expand=True,
    )