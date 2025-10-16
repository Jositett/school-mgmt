import flet as ft
from datetime import date, timedelta
from database import get_attendance_for_student, update_attendance
from models import AttendanceRecord, Student


def create_attendance_view(page: ft.Page, show_snackbar, selected_student_for_attendance):
    """Create the attendance management view."""
    student_dropdown = ft.Dropdown(
        label="Select Student",
        hint_text="Choose a student",
        # No icon for dropdown
        on_change=lambda e: load_attendance_records(),
        expand=True,
    )

    date_picker_field = ft.TextField(
        label="Date",
        value=str(date.today()),
        prefix_icon=ft.Icons.CALENDAR_TODAY,
        width=200,
        read_only=True,
    )

    status_dropdown = ft.Dropdown(
        label="Status",
        # No icon for dropdown
        width=200,
        options=[
            ft.dropdown.Option("Present"),
            ft.dropdown.Option("Absent"),
            ft.dropdown.Option("Late"),
        ],
        value="Present",
    )

    attendance_list_view = ft.ListView(
        spacing=10,
        padding=20,
        expand=True,
    )

    def load_students():
        """Load all students into dropdown."""
        from database import get_all_students
        students = get_all_students()
        student_dropdown.options = [
            ft.dropdown.Option(key=str(s.id), text=f"{s.name} - Class {s.class_name}" if s.class_name else f"{s.name} - No Class Assigned")
            for s in students
        ]
        if students:
            student_dropdown.value = str(students[0].id)
            selected_student_for_attendance = students[0].id
        page.update()

    def load_attendance_records():
        """Load attendance records for selected student."""
        if not student_dropdown.value:
            return

        selected_student_for_attendance = int(student_dropdown.value)
        start_date = str((date.today() - timedelta(days=30)))
        end_date = str(date.today())

        records = get_attendance_for_student(
            selected_student_for_attendance,
            start_date,
            end_date
        )

        attendance_list_view.controls.clear()

        if not records:
            attendance_list_view.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.EVENT_BUSY, size=64, color=ft.Colors.GREY_400),
                        ft.Text("No attendance records found", size=16, color=ft.Colors.GREY_600),
                        ft.Text("(Last 30 days)", size=12, color=ft.Colors.GREY_500),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=40,
                )
            )
        else:
            for record in records:
                status_color = {
                    "Present": ft.Colors.GREEN_700,
                    "Absent": ft.Colors.RED_700,
                    "Late": ft.Colors.ORANGE_700,
                }.get(record.status, ft.Colors.GREY_700)

                attendance_list_view.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row([
                                ft.Column([
                                    ft.Text(record.date, weight=ft.FontWeight.BOLD),
                                    ft.Text(record.status, color=status_color, size=12),
                                ]),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    icon_color=ft.Colors.BLUE_700,
                                    tooltip="Edit",
                                    on_click=lambda e, r=record: edit_attendance_record(r),
                                ),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=15,
                        ),
                    )
                )
        page.update()

    def edit_attendance_record(record: AttendanceRecord):
        """Edit an attendance record."""
        date_picker_field.value = record.date
        status_dropdown.value = record.status
        page.update()

    def save_attendance(e):
        """Save attendance record."""
        if selected_student_for_attendance is None:
            show_snackbar("Please select a student!", True)
            return

        if not date_picker_field.value or not status_dropdown.value:
            show_snackbar("Please fill all fields!", True)
            return

        if update_attendance(
            selected_student_for_attendance,
            date_picker_field.value,
            status_dropdown.value
        ):
            show_snackbar("Attendance updated successfully!")
            load_attendance_records()
            # Reset form
            date_picker_field.value = str(date.today())
            status_dropdown.value = "Present"
            page.update()
        else:
            show_snackbar("Error updating attendance!", True)

    def open_calendar(e):
        """Open date picker dialog."""
        def handle_date_change(e):
            date_picker_field.value = e.control.value.strftime("%Y-%m-%d")
            page.update()

        date_picker = ft.DatePicker(
            on_change=handle_date_change,
            first_date=date(2020, 1, 1),
            last_date=date(2030, 12, 31),
        )
        page.overlay.append(date_picker)
        date_picker.open = True
        page.update()

    # Make date field clickable to open calendar
    date_picker_field.on_click = open_calendar

    # Initialize
    load_students()
    if student_dropdown.value:
        load_attendance_records()

    # Build view
    return ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Text("Attendance Management", size=24, weight=ft.FontWeight.BOLD),
                padding=20,
            ),
            ft.Divider(height=1),
            ft.Container(
                content=ft.Column([
                    ft.Text("Record Attendance", size=16, weight=ft.FontWeight.W_500),
                    student_dropdown,
                    ft.Row([
                        date_picker_field,
                        status_dropdown,
                        ft.ElevatedButton(
                            "Save Attendance",
                            icon=ft.Icons.SAVE,
                            on_click=save_attendance,
                        ),
                    ], spacing=15),
                ], spacing=15),
                padding=20,
            ),
            ft.Divider(height=1),
            ft.Container(
                content=ft.Column([
                    ft.Text("Recent Attendance Records (Last 30 Days)", size=16, weight=ft.FontWeight.W_500),
                    ft.Container(
                        content=attendance_list_view,
                        expand=True,
                    ),
                ], spacing=10),
                padding=20,
                expand=True,
            ),
        ], spacing=0, expand=True),
        expand=True,
    )
