import flet as ft
import cv2
import base64
import time
from database import get_all_students
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

    status_text = ft.Text("", size=14)

    def load_students():
        """Load students into dropdown."""
        students = get_all_students()
        student_dropdown.options = [
            ft.dropdown.Option(key=str(s.id), text=s.name) for s in students
        ]
        if students:
            student_dropdown.value = str(students[0].id)

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
                status_text.value = "Error: Not enough frames captured. Make sure webcam is working."
                show_snackbar("Face enrolment failed!", True)
            else:
                if FaceService().enrol_student(student_id, frames):
                    status_text.value = "Face enrolled successfully!"
                    show_snackbar("Face enrolled successfully!")
                else:
                    status_text.value = "Error: No face detected. Try again with better lighting."
                    show_snackbar("Face enrolment failed!", True)

        except Exception as ex:
            status_text.value = f"Error: {str(ex)}"
            show_snackbar("Face enrolment failed!", True)

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