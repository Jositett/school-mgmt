import flet as ft
import cv2
import base64
import time
import threading
import numpy as np
import os
from datetime import date
from database import get_student_by_id, update_attendance, get_current_attendance_status, get_attendance_for_student

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

# Use the fast JS-based face service (no dlib dependency)
from face_service_js import FaceServiceJS as FaceService
print("Using fast OpenCV+JavaScript face recognition for attendance (no dlib dependency)")

# 1×1 transparent PNG base64 (valid, tiny)
PLACEHOLDER_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def create_live_attendance_view(page: ft.Page, show_snackbar):
    """Create modern responsive live face attendance view."""

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

    image_display = ft.Image(
        src_base64=PLACEHOLDER_B64,
        width=camera_width,
        height=camera_height,
        fit=ft.ImageFit.CONTAIN,
        border_radius=15,
    )

    # Live attendance status indicator
    status_indicator = ft.Container(
        content=ft.Row([
            ft.Container(
                width=12,
                height=12,
                border_radius=6,
                bgcolor=ft.Colors.GREY_400,
            ),
            ft.Text("Ready", size=14, color=ft.Colors.GREY_600),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=15, vertical=8),
        border_radius=20,
        bgcolor=ft.Colors.GREY_100,
    )

    # Recognized students list
    recognized_list = ft.Column(spacing=8)
    # Track students already shown in the recognized list
    shown_students = set()

    status_text = ft.Text("Click 'Start Camera' to begin live attendance", size=14)

    start_btn = ft.ElevatedButton(
        "Start Camera",
        icon=ft.Icons.PLAY_ARROW,
        height=50,
        width=160 if not is_mobile else None,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.GREEN_600,
            color=ft.Colors.WHITE,
        ),
    )

    stop_btn = ft.ElevatedButton(
        "Stop & Save",
        icon=ft.Icons.STOP,
        disabled=True,
        height=50,
        width=160 if not is_mobile else None,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.RED_600,
            color=ft.Colors.WHITE,
        ),
    )

    students_present = set()
    attendance_date = str(date.today())
    is_running = False

    def start_live_attendance(e):
        nonlocal is_running, students_present, shown_students
        is_running = True
        students_present = set()
        shown_students = set()
        recognized_list.controls.clear()  # Clear the list
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
                    try:
                        faces = FaceService().recognise(frame)
                        if faces:
                            all_detected = {student_id for student_id, _ in faces}
                            # Filter out students already marked for today
                            new_students = {sid for sid in all_detected if not get_attendance_for_student(sid, attendance_date, attendance_date)}
                            students_present.update(new_students)
                            newly_detected = new_students - shown_students

                            # Update recognized_list with newly detected students
                            if newly_detected:
                                for sid in newly_detected:
                                    student = get_student_by_id(sid)
                                    if student:
                                        # Get current attendance status based on time
                                        attendance_status = get_current_attendance_status(sid)
                                        # Add to list with appropriate color
                                        color = ft.Colors.GREEN_700 if attendance_status == "Present" else ft.Colors.ORANGE_700 if attendance_status == "Late" else ft.Colors.RED_700
                                        recognized_list.controls.append(
                                            ft.Container(
                                                content=ft.Row([
                                                    ft.Container(width=8, height=8, bgcolor=color, border_radius=4),
                                                    ft.Text(f"{student.name}", size=11, color=color),
                                                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                                padding=ft.padding.symmetric(vertical=4, horizontal=8),
                                                border_radius=8,
                                            )
                                        )
                                        shown_students.add(sid)
                                page.update()  # Update UI after adding new students

                            # Update status with recognized students and their attendance status
                            student_info = []
                            for sid in new_students:
                                student = get_student_by_id(sid)
                                if student:
                                    # Get current attendance status based on time
                                    attendance_status = get_current_attendance_status(sid)
                                    student_info.append(f"{student.name} ({attendance_status})")
                            if student_info:
                                status_text.value = f"Recognized: {', '.join(student_info)}"
                    except Exception as recognition_error:
                        # Log recognition errors but don't crash the thread
                        print(f"Face recognition error: {recognition_error}")
                        pass

                # Draw bounding boxes and labels on frame for visualization
                display_frame = frame.copy()
                try:
                    # Always try to detect faces for visualization - all detected faces
                    all_recognized_faces = faces if 'faces' in locals() and faces else []

                    for face_data in all_recognized_faces:
                        student_id, confidence = face_data
                        student = get_student_by_id(student_id)
                        if student:
                            # Get attendance status for this student
                            attendance_status = get_current_attendance_status(student_id)
                            # Check if already marked today
                            is_already_marked = bool(get_attendance_for_student(student_id, attendance_date, attendance_date))

                            # Set color based on status and marked status
                            if is_already_marked:
                                color = (128, 128, 128)  # Gray for already marked
                            elif attendance_status == "Present":
                                color = (0, 255, 0)  # Green
                            elif attendance_status == "Late":
                                color = (0, 255, 255)  # Yellow
                            else:  # Absent
                                color = (0, 0, 255)  # Red

                            # For visualization, we need face locations - using simple approach with face cascade
                            if FACE_AVAILABLE and face_recognition:
                                rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                                face_locations = face_recognition.face_locations(rgb, model="hog")
                                # Simple matching by size - this is approximate
                                for (top, right, bottom, left) in face_locations[:len(all_recognized_faces)]:  # Limit to detected count
                                    # Draw rectangle
                                    cv2.rectangle(display_frame, (left, top), (right, bottom), color, 2)

                                    # Draw label background and text
                                    label_text = f"{student.name}: {attendance_status}"
                                    if is_already_marked:
                                        label_text += " (Marked)"
                                    cv2.rectangle(display_frame, (left, bottom - 25), (right, bottom), color, cv2.FILLED)
                                    cv2.putText(display_frame, label_text, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)
                                    break  # Only label the first match
                except Exception as viz_error:
                    print(f"Face recognition visualization error: {viz_error}")
                # Convert frame to base64 for display
                _, buffer = cv2.imencode('.jpg', display_frame)
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

        # Mark attendance for all recognized students with their current status
        marked_count = 0
        for student_id in students_present:
            # Get the current attendance status based on time
            attendance_status = get_current_attendance_status(student_id)
            if update_attendance(student_id, attendance_date, attendance_status):
                marked_count += 1

        status_text.value = f"Attendance completed! Marked {marked_count} student(s) as present for {attendance_date}"
        image_display.src_base64 = PLACEHOLDER_B64  # Reset to placeholder
        show_snackbar(f"Marked {marked_count} student(s) present")
        page.update()

    start_btn.on_click = start_live_attendance
    stop_btn.on_click = stop_live_attendance

    # Create responsive layout
    if is_mobile:
        # Mobile layout - stacked vertically
        return ft.Container(
            content=ft.Column([
                # Header
                ft.Container(
                    content=ft.Column([
                        ft.Text("📹 Live Face Attendance", size=20, weight=ft.FontWeight.BOLD),
                        status_indicator,
                    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(vertical=20),
                ),

                # Camera display
                ft.Container(
                    content=ft.Container(
                        content=image_display,
                        alignment=ft.alignment.center,
                        bgcolor=ft.Colors.BLACK,
                        height=camera_height + 20,
                        border_radius=20,
                    ),
                    alignment=ft.alignment.center,
                    margin=ft.margin.symmetric(horizontal=10),
                ),

                # Controls section
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=status_text,
                            alignment=ft.alignment.center,
                            padding=ft.padding.symmetric(vertical=10),
                        ),
                        ft.Container(
                            content=ft.Row([
                                start_btn,
                                stop_btn,
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                            alignment=ft.alignment.center,
                            padding=ft.padding.symmetric(vertical=10),
                        ),
                    ], spacing=10),
                    margin=ft.margin.symmetric(horizontal=20, vertical=10),
                ),

                # Instructions card
                ft.Container(
                    content=ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE_600),
                                    ft.Text("Instructions", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600),
                                ], spacing=8),
                                ft.Text("• Ensure good lighting for best recognition", size=12),
                                ft.Text("• Face the camera clearly", size=12),
                                ft.Text("• Students are marked automatically", size=12),
                                ft.Text("• Green: On time, Yellow: Late, Red: Absent", size=12, color=ft.Colors.GREY_700),
                                ft.Divider(height=10),
                                ft.Text("Today: " + attendance_date, size=12, color=ft.Colors.GREY_600),
                            ], spacing=5),
                            padding=15,
                        ),
                        elevation=2,
                    ),
                    margin=ft.margin.symmetric(horizontal=20, vertical=10),
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
                                ft.Text("📹 Live Face Attendance", size=24, weight=ft.FontWeight.BOLD),
                                status_indicator,
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=ft.padding.symmetric(vertical=20, horizontal=20),
                        ),

                        # Camera display
                        ft.Container(
                            content=ft.Container(
                                content=image_display,
                                alignment=ft.alignment.center,
                                bgcolor=ft.Colors.BLACK,
                                height=camera_height + 40,
                                border_radius=20,
                            ),
                            alignment=ft.alignment.center,
                            margin=ft.margin.symmetric(horizontal=20),
                        ),

                        # Controls and status
                        ft.Container(
                            content=ft.Column([
                                ft.Container(
                                    content=status_text,
                                    alignment=ft.alignment.center,
                                    padding=ft.padding.symmetric(vertical=10),
                                ),
                                ft.Container(
                                    content=ft.Row([
                                        start_btn,
                                        stop_btn,
                                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                                    alignment=ft.alignment.center,
                                ),
                            ], spacing=15),
                            margin=ft.margin.symmetric(horizontal=20, vertical=20),
                        ),
                    ], spacing=0),
                    expand=True,
                ),

                # Sidebar with instructions and info
                ft.VerticalDivider(width=1),
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Text("📋 Session Info", size=18, weight=ft.FontWeight.BOLD),
                            padding=ft.padding.all(20),
                        ),

                        # Instructions card
                        ft.Container(
                            content=ft.Card(
                                content=ft.Container(
                                    content=ft.Column([
                                        ft.Row([
                                            ft.Icon(ft.Icons.LIGHT_MODE, color=ft.Colors.AMBER_600),
                                            ft.Text("Recognition Tips", weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_700),
                                        ], spacing=8),
                                        ft.Text("• Ensure bright, even lighting", size=12),
                                        ft.Text("• Face camera directly", size=12),
                                        ft.Text("• Remove glasses/sunglasses", size=12),
                                        ft.Text("• Keep face steady", size=12),
                                        ft.Divider(height=15),
                                        ft.Row([
                                            ft.Container(width=12, height=12, bgcolor=ft.Colors.GREEN_500, border_radius=6),
                                            ft.Text("Present (On time)", size=11),
                                        ], spacing=8),
                                        ft.Row([
                                            ft.Container(width=12, height=12, bgcolor=ft.Colors.YELLOW_500, border_radius=6),
                                            ft.Text("Late (+30 mins)", size=11),
                                        ], spacing=8),
                                        ft.Row([
                                            ft.Container(width=12, height=12, bgcolor=ft.Colors.RED_500, border_radius=6),
                                            ft.Text("Absent (After session)", size=11),
                                        ], spacing=8),
                                    ], spacing=8),
                                    padding=15,
                                ),
                                elevation=2,
                            ),
                            margin=ft.margin.symmetric(horizontal=15),
                        ),

                        # Session info
                        ft.Container(
                            content=ft.Card(
                                content=ft.Container(
                                    content=ft.Column([
                                        ft.Row([
                                            ft.Icon(ft.Icons.CALENDAR_TODAY, color=ft.Colors.BLUE_600),
                                            ft.Text("Today's Session", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600),
                                        ], spacing=8),
                                        ft.Text(f"Date: {attendance_date}", size=12),
                                        ft.Text("Status: Active", size=12, color=ft.Colors.GREEN_600),
                                        ft.Divider(height=10),
                                        ft.Text("Students Recognized:", size=12, weight=ft.FontWeight.BOLD),
                                        ft.Container(
                                            content=recognized_list,
                                            height=150,
                                            bgcolor=ft.Colors.GREY_50,
                                            border_radius=8,
                                            padding=10,
                                        ),
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
