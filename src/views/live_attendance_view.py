import flet as ft
import cv2
import base64
import time
import threading
from datetime import date
from database import get_student_by_id, update_attendance
from face_service import FaceService


def create_live_attendance_view(page: ft.Page, show_snackbar):
    """Create live face attendance view."""
    image_display = ft.Image(
        src_base64="",
        width=640,
        height=480,
        fit=ft.ImageFit.CONTAIN,
    )

    start_btn = ft.ElevatedButton(
        "Start Live Attendance",
        icon=ft.Icons.PLAY_ARROW,
    )

    stop_btn = ft.ElevatedButton(
        "Stop & Save Attendance",
        icon=ft.Icons.STOP,
        disabled=True,
    )

    status_text = ft.Text("Click 'Start Live Attendance' to begin", size=14)
    students_present = set()
    attendance_date = str(date.today())
    is_running = False

    def start_live_attendance(e):
        nonlocal is_running, students_present
        is_running = True
        students_present = set()
        start_btn.disabled = True
        stop_btn.disabled = False
        status_text.value = "Live attendance running... Students detected will be marked present."
        page.update()

        def capture_loop():
            nonlocal is_running
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                status_text.value = "Error: Cannot access webcam"
                page.update()
                return

            frame_count = 0
            while is_running:
                ret, frame = cap.read()
                if not ret:
                    break

                # Process every 10th frame to reduce CPU usage
                if frame_count % 10 == 0:
                    faces = FaceService().recognise(frame)
                    if faces:
                        new_students = {student_id for student_id, _ in faces}
                        students_present.update(new_students)

                        # Update status with recognized students
                        student_names = []
                        for sid in new_students:
                            student = get_student_by_id(sid)
                            if student:
                                student_names.append(student.name)
                        if student_names:
                            status_text.value = f"Recognized: {', '.join(student_names)}"

                # Convert frame to base64 for display
                _, buffer = cv2.imencode('.jpg', frame)
                image_display.src_base64 = base64.b64encode(buffer).decode()
                page.update()

                frame_count += 1
                time.sleep(0.1)  # ~10 FPS

            cap.release()

        # Run capture in thread to not block UI
        threading.Thread(target=capture_loop, daemon=True).start()

    def stop_live_attendance(e):
        nonlocal is_running, students_present, attendance_date
        is_running = False
        start_btn.disabled = False
        stop_btn.disabled = True

        # Mark attendance for all recognized students
        marked_count = 0
        for student_id in students_present:
            if update_attendance(student_id, attendance_date, "Present"):
                marked_count += 1

        status_text.value = f"Attendance completed! Marked {marked_count} student(s) as present for {attendance_date}"
        image_display.src_base64 = ""
        show_snackbar(f"Marked {marked_count} student(s) present")
        page.update()

    start_btn.on_click = start_live_attendance
    stop_btn.on_click = stop_live_attendance

    return ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Text("Live Face Attendance", size=24, weight=ft.FontWeight.BOLD),
                padding=20,
            ),
            ft.Divider(height=1),
            ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=image_display,
                        alignment=ft.alignment.center,
                        padding=20,
                    ),
                    ft.Row([
                        start_btn,
                        stop_btn,
                    ], spacing=15),
                    status_text,
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.SECURITY, color=ft.Colors.GREEN_700),
                            ft.Text("• Only students with enrolled faces will be recognized", size=12),
                            ft.Text("• Students will be marked as present automatically", size=12),
                            ft.Text("• Recognition works best with good lighting", size=12),
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