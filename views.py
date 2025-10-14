"""
UI view modules for School Management System
"""
import flet as ft
from datetime import date, timedelta
import time
import threading
import base64
import cv2

from models import Student
from database import (
    get_all_classes, add_class, get_all_students, get_student_by_id,
    add_student, update_student, delete_student,
    get_attendance_for_student, update_attendance,
    get_fees_for_student, add_fee_record, update_fee_status, delete_fee_record
)
from face_service import FaceService
from utils import show_snackbar, export_students_to_csv


class StudentView:
    """Student management view."""

    def __init__(self):
        self.edit_student_id = None

    def create_view(self, page: ft.Page, current_user: str):
        """Create the student management view."""
        # Form fields - Use prefix_icon (works in 0.28.3 despite deprecation warning)
        name_field = ft.TextField(
            label="Student Name",
            hint_text="Enter full name",
            prefix_icon=ft.Icons.PERSON,
            expand=True,
        )

        age_field = ft.TextField(
            label="Age",
            hint_text="5-18",
            prefix_icon=ft.Icons.CAKE,
            width=120,
            input_filter=ft.NumbersOnlyInputFilter(),
        )

        grade_field = ft.TextField(
            label="Grade",
            hint_text="e.g., 10th",
            prefix_icon=ft.Icons.SCHOOL,
            width=150,
        )

        class_dropdown = ft.Dropdown(
            label="Class",
            hint_text="Select class",
            # No icon for dropdown in 0.28.3
            width=200,
        )

        search_field = ft.TextField(
            label="Search",
            hint_text="Search by name, grade, or class",
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: self.update_student_list(students_list, e.control.value),
            expand=True,
        )

        students_list = ft.ListView(
            spacing=10,
            padding=20,
            expand=True,
        )

        def load_classes():
            """Load classes into dropdown."""
            classes = get_all_classes()
            class_dropdown.options = [
                ft.dropdown.Option(key=str(c.id), text=c.name) for c in classes
            ]
            if classes:
                class_dropdown.value = str(classes[0].id)

        def update_student_list():
            """Update the student list display."""
            search_query = search_field.value
            students = get_all_students(search_query)
            students_list.controls.clear()

            if not students:
                students_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.GREY_400),
                            ft.Text("No students found", size=16, color=ft.Colors.GREY_600),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=40,
                    )
                )
            else:
                for student in students:
                    students_list.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.CircleAvatar(
                                            content=ft.Text(
                                                student.name[0].upper(),
                                                size=20,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            bgcolor=ft.Colors.BLUE_200,
                                            color=ft.Colors.BLUE_900,
                                        ),
                                        width=50,
                                    ),
                                    ft.Column([
                                        ft.Text(student.name, weight=ft.FontWeight.BOLD, size=16),
                                        ft.Row([
                                            ft.Icon(ft.Icons.CAKE, size=16, color=ft.Colors.GREY_600),
                                            ft.Text(f"{student.age} years", size=12, color=ft.Colors.GREY_600),
                                            ft.VerticalDivider(width=1),
                                            ft.Icon(ft.Icons.SCHOOL, size=16, color=ft.Colors.GREY_600),
                                            ft.Text(f"Grade {student.grade}", size=12, color=ft.Colors.GREY_600),
                                            ft.VerticalDivider(width=1),
                                            ft.Icon(ft.Icons.CLASS_, size=16, color=ft.Colors.GREY_600),
                                            ft.Text(student.class_name or "No class", size=12, color=ft.Colors.GREY_600),
                                        ], spacing=5),
                                    ], spacing=5, expand=True),
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT,
                                            icon_color=ft.Colors.BLUE_700,
                                            tooltip="Edit",
                                            on_click=lambda e, s=student: self.edit_student(s, name_field, age_field, grade_field, class_dropdown),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.CALENDAR_TODAY,
                                            icon_color=ft.Colors.GREEN_700,
                                            tooltip="Attendance",
                                            on_click=lambda e, s=student: self.show_attendance_for_student(page, s),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.PAYMENTS,
                                            icon_color=ft.Colors.ORANGE_700,
                                            tooltip="Fees",
                                            on_click=lambda e, s=student: self.show_fees_for_student(page, s),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            icon_color=ft.Colors.RED_700,
                                            tooltip="Delete",
                                            on_click=lambda e, sid=student.id: confirm_delete_student(page, sid),
                                        ),
                                    ], spacing=0),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                padding=15,
                            ),
                        )
                    )
            page.update()

        def edit_student(student: Student):
            """Load student data for editing."""
            self.edit_student_id = student.id
            name_field.value = student.name
            age_field.value = str(student.age)
            grade_field.value = student.grade
            class_dropdown.value = str(student.class_id) if student.class_id else None
            page.update()

        def clear_form():
            """Clear all form fields."""
            self.edit_student_id = None
            name_field.value = ""
            age_field.value = ""
            grade_field.value = ""
            load_classes()
            page.update()

        def save_student(e):
            """Save or update student."""
            if not name_field.value or not age_field.value or not grade_field.value:
                show_snackbar(page, "All fields are required!", True)
                return

            try:
                age = int(age_field.value)
                if age < 5 or age > 18:
                    show_snackbar(page, "Age must be between 5 and 18!", True)
                    return

                class_id = int(class_dropdown.value) if class_dropdown.value else None

                if self.edit_student_id is None:
                    if add_student(name_field.value, age, grade_field.value, class_id):
                        show_snackbar(page, "Student added successfully!")
                        clear_form()
                        update_student_list()
                    else:
                        show_snackbar(page, "Error adding student!", True)
                else:
                    if update_student(self.edit_student_id, name_field.value, age,
                                    grade_field.value, class_id):
                        show_snackbar(page, "Student updated successfully!")
                        clear_form()
                        update_student_list()
                    else:
                        show_snackbar(page, "Error updating student!", True)
            except ValueError:
                show_snackbar(page, "Invalid age value!", True)

        def confirm_delete_student(student_id: int):
            """Show confirmation dialog for deleting student."""
            def delete_confirmed(e):
                if delete_student(student_id):
                    show_snackbar(page, "Student deleted successfully!")
                    update_student_list()
                else:
                    show_snackbar(page, "Error deleting student!", True)
                dialog.open = False
                page.update()

            def cancel_delete(e):
                dialog.open = False
                page.update()

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirm Delete"),
                content=ft.Text("Are you sure you want to delete this student? All attendance and fee records will also be deleted."),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel_delete),
                    ft.TextButton("Delete", on_click=delete_confirmed, style=ft.ButtonStyle(
                        color=ft.Colors.RED_700,
                    )),
                ],
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        def export_csv(e):
            """Export students to CSV."""
            try:
                filename = export_students_to_csv()
                show_snackbar(page, f"Exported to: {filename}")
            except Exception as ex:
                show_snackbar(page, f"Export failed: {str(ex)}", True)

        def add_class_dialog(e):
            """Show dialog to add new class."""
            class_name_field = ft.TextField(
                label="Class Name",
                hint_text="e.g., Grade 10A",
                autofocus=True,
            )

            def save_class(e):
                if class_name_field.value and add_class(class_name_field.value):
                    load_classes()
                    show_snackbar(page, "Class added successfully!")
                    dialog.open = False
                    page.update()
                else:
                    show_snackbar(page, "Error adding class! Name might be duplicate.", True)

            def close_dialog(e):
                dialog.open = False
                page.update()

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Add New Class"),
                content=ft.Container(
                    content=class_name_field,
                    width=300,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=close_dialog),
                    ft.TextButton("Add", on_click=save_class),
                ],
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        # Initialize
        load_classes()
        update_student_list()

        # Build view
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text("Student Management", size=24, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.ElevatedButton(
                                "Export CSV",
                                icon=ft.Icons.DOWNLOAD,
                                on_click=export_csv,
                            ),
                        ]),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=20,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Column([
                        search_field,
                        ft.Text("Add / Edit Student", size=16, weight=ft.FontWeight.W_500),
                        ft.Row([
                            name_field,
                        ]),
                        ft.Row([
                            age_field,
                            grade_field,
                            class_dropdown,
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE,
                                icon_color=ft.Colors.GREEN_700,
                                tooltip="Add New Class",
                                on_click=add_class_dialog,
                            ),
                        ]),
                        ft.Row([
                            ft.ElevatedButton(
                                "Save Student" if self.edit_student_id is None else "Update Student",
                                icon=ft.Icons.SAVE,
                                on_click=save_student,
                            ),
                            ft.OutlinedButton(
                                "Clear",
                                icon=ft.Icons.CLEAR,
                                on_click=lambda e: clear_form(),
                            ),
                        ]),
                    ], spacing=15),
                    padding=20,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Students List", size=16, weight=ft.FontWeight.W_500),
                        ft.Container(
                            content=students_list,
                            expand=True,
                        ),
                    ], spacing=10),
                    padding=20,
                    expand=True,
                ),
            ], spacing=0, expand=True),
            expand=True,
        )

    def edit_student(self, student: Student, name_field, age_field, grade_field, class_dropdown):
        """Load student data for editing."""
        self.edit_student_id = student.id
        name_field.value = student.name
        age_field.value = str(student.age)
        grade_field.value = student.grade
        class_dropdown.value = str(student.class_id) if student.class_id else None

    def show_attendance_for_student(self, page: ft.Page, student: Student):
        """Switch to attendance view for specific student."""
        page.current_view = "attendance"
        page.selected_student_for_attendance = student.id
        page.show_main_app()

    def show_fees_for_student(self, page: ft.Page, student: Student):
        """Switch to fees view for specific student."""
        page.current_view = "fees"
        page.selected_student_for_fees = student.id
        page.show_main_app()

    def update_student_list(self, students_list, search_query=""):
        """Update student list with optional search."""
        students = get_all_students(search_query)
        students_list.controls.clear()

        if not students:
            students_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.GREY_400),
                        ft.Text("No students found", size=16, color=ft.Colors.GREY_600),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=40,
                )
            )
        else:
            for student in students:
                students_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row([
                                ft.Container(
                                    content=ft.CircleAvatar(
                                        content=ft.Text(
                                            student.name[0].upper(),
                                            size=20,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        bgcolor=ft.Colors.BLUE_200,
                                        color=ft.Colors.BLUE_900,
                                    ),
                                    width=50,
                                ),
                                ft.Column([
                                    ft.Text(student.name, weight=ft.FontWeight.BOLD, size=16),
                                    ft.Row([
                                        ft.Icon(ft.Icons.CAKE, size=16, color=ft.Colors.GREY_600),
                                        ft.Text(f"{student.age} years", size=12, color=ft.Colors.GREY_600),
                                        ft.VerticalDivider(width=1),
                                        ft.Icon(ft.Icons.SCHOOL, size=16, color=ft.Colors.GREY_600),
                                        ft.Text(f"Grade {student.grade}", size=12, color=ft.Colors.GREY_600),
                                        ft.VerticalDivider(width=1),
                                        ft.Icon(ft.Icons.CLASS_, size=16, color=ft.Colors.GREY_600),
                                        ft.Text(student.class_name or "No class", size=12, color=ft.Colors.GREY_600),
                                    ], spacing=5),
                                ], spacing=5, expand=True),
                                ft.Row([
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        icon_color=ft.Colors.BLUE_700,
                                        tooltip="Edit",
                                        on_click=lambda e, s=student: self.edit_student(s),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.CALENDAR_TODAY,
                                        icon_color=ft.Colors.GREEN_700,
                                        tooltip="Attendance",
                                        on_click=lambda e, s=student: self.show_attendance_for_student(page, s),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.PAYMENTS,
                                        icon_color=ft.Colors.ORANGE_700,
                                        tooltip="Fees",
                                        on_click=lambda e, s=student: self.show_fees_for_student(page, s),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED_700,
                                        tooltip="Delete",
                                    ),
                                ], spacing=0),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=15,
                        ),
                    )
                )

        page.update()


class AttendanceView:
    """Attendance management view."""

    def __init__(self):
        self.selected_student_for_attendance = None

    def create_view(self, page: ft.Page, current_user: str):
        """Create the attendance management view."""
        student_dropdown = ft.Dropdown(
            label="Select Student",
            hint_text="Choose a student",
            # No icon for dropdown
            on_change=lambda e: self.load_attendance_records(page, attendance_list, e.control.value),
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

        attendance_list = ft.ListView(
            spacing=10,
            padding=20,
            expand=True,
        )

        def load_students():
            """Load all students into dropdown."""
            students = get_all_students()
            student_dropdown.options = [
                ft.dropdown.Option(key=str(s.id), text=f"{s.name} - Grade {s.grade}")
                for s in students
            ]
            if students:
                student_dropdown.value = str(students[0].id)
                self.selected_student_for_attendance = students[0].id
            page.update()

        def load_attendance_records(selected_student_id=None):
            """Load attendance records for selected student."""
            if not selected_student_id and not student_dropdown.value:
                return

            student_id = selected_student_id or int(student_dropdown.value)
            self.selected_student_for_attendance = student_id

            start_date = str((date.today() - timedelta(days=30)))
            end_date = str(date.today())

            records = get_attendance_for_student(
                student_id,
                start_date,
                end_date
            )

            attendance_list.controls.clear()

            if not records:
                attendance_list.controls.append(
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

                    attendance_list.controls.append(
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

        def edit_attendance_record(record):
            """Edit an attendance record."""
            date_picker_field.value = record.date
            status_dropdown.value = record.status
            page.update()

        def save_attendance(e):
            """Save attendance record."""
            if self.selected_student_for_attendance is None:
                show_snackbar(page, "Please select a student!", True)
                return

            if not date_picker_field.value or not status_dropdown.value:
                show_snackbar(page, "Please fill all fields!", True)
                return

            if update_attendance(
                self.selected_student_for_attendance,
                date_picker_field.value,
                status_dropdown.value
            ):
                show_snackbar(page, "Attendance updated successfully!")
                load_attendance_records()
                # Reset form
                date_picker_field.value = str(date.today())
                status_dropdown.value = "Present"
                page.update()
            else:
                show_snackbar(page, "Error updating attendance!", True)

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
            page.update()
            date_picker.pick_date()

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
                            content=attendance_list,
                            expand=True,
                        ),
                    ], spacing=10),
                    padding=20,
                    expand=True,
                ),
            ], spacing=0, expand=True),
            expand=True,
        )


class FeesView:
    """Fees management view."""

    def __init__(self):
        self.selected_student_for_fees = None

    def create_view(self, page: ft.Page, current_user: str):
        """Create the fees management view."""
        student_dropdown = ft.Dropdown(
            label="Select Student",
            hint_text="Choose a student",
            # No icon for dropdown
            on_change=lambda e: self.load_fees_records(page, fees_list, e.control.value),
            expand=True,
        )

        amount_field = ft.TextField(
            label="Amount",
            hint_text="Enter amount",
            prefix_icon=ft.Icons.MONETIZATION_ON,
            width=150,
            input_filter=ft.NumbersOnlyInputFilter(),
        )

        due_date_field = ft.TextField(
            label="Due Date",
            value=str(date.today()),
            prefix_icon=ft.Icons.CALENDAR_TODAY,
            width=200,
            read_only=True,
        )

        description_field = ft.TextField(
            label="Description",
            hint_text="Optional description",
            prefix_icon=ft.Icons.DESCRIPTION,
            expand=True,
        )

        fees_list = ft.ListView(
            spacing=10,
            padding=20,
            expand=True,
        )

        def load_students():
            """Load all students into dropdown."""
            students = get_all_students()
            student_dropdown.options = [
                ft.dropdown.Option(key=str(s.id), text=f"{s.name} - Grade {s.grade}")
                for s in students
            ]
            if students:
                student_dropdown.value = str(students[0].id)
                self.selected_student_for_fees = students[0].id
            page.update()

        def load_fees_records(selected_student_id=None):
            """Load fees records for selected student."""
            if not selected_student_id and not student_dropdown.value:
                return

            student_id = selected_student_id or int(student_dropdown.value)
            self.selected_student_for_fees = student_id

            records = get_fees_for_student(student_id)

            fees_list.controls.clear()

            if not records:
                fees_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.RECEIPT_LONG, size=64, color=ft.Colors.GREY_400),
                            ft.Text("No fee records found", size=16, color=ft.Colors.GREY_600),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=40,
                    )
                )
            else:
                total_pending = 0
                total_paid = 0

                for record in records:
                    if record.status == "Paid":
                        total_paid += record.amount
                    else:
                        total_pending += record.amount

                    status_color = ft.Colors.GREEN_700 if record.status == "Paid" else ft.Colors.RED_700

                    fees_list.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Row([
                                        ft.Text(f"${record.amount:.2f}", weight=ft.FontWeight.BOLD, size=16),
                                        ft.Text(record.status, color=status_color, size=12),
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                    ft.Row([
                                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=14, color=ft.Colors.GREY_600),
                                        ft.Text(f"Due: {record.due_date}", size=12, color=ft.Colors.GREY_600),
                                        ft.VerticalDivider(width=1),
                                        ft.Icon(ft.Icons.PAYMENT, size=14, color=ft.Colors.GREY_600),
                                        ft.Text(f"Paid: {record.paid_date or 'N/A'}", size=12, color=ft.Colors.GREY_600),
                                    ], spacing=5),
                                    ft.Text(record.description or "", size=12, color=ft.Colors.GREY_700),
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.PAYMENT,
                                            icon_color=ft.Colors.BLUE_700,
                                            tooltip="Mark as Paid",
                                            on_click=lambda e, r=record: mark_fee_paid(page, r),
                                            disabled=record.status == "Paid",
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            icon_color=ft.Colors.RED_700,
                                            tooltip="Delete",
                                            on_click=lambda e, fid=record.id: confirm_delete_fee(page, fid),
                                        ),
                                    ], spacing=0),
                                ], spacing=5),
                                padding=15,
                            ),
                        )
                    )

                # Add summary card
                fees_list.controls.insert(
                    0,
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("Fee Summary", weight=ft.FontWeight.BOLD, size=16),
                                ft.Divider(height=10),
                                ft.Row([
                                    ft.Column([
                                        ft.Text("Total Pending:", size=14, color=ft.Colors.RED_700),
                                        ft.Text(f"${total_pending:.2f}", weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.RED_700),
                                    ]),
                                    ft.VerticalDivider(width=1),
                                    ft.Column([
                                        ft.Text("Total Paid:", size=14, color=ft.Colors.GREEN_700),
                                        ft.Text(f"${total_paid:.2f}", weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.GREEN_700),
                                    ]),
                                    ft.VerticalDivider(width=1),
                                    ft.Column([
                                        ft.Text("Total Fees:", size=14),
                                        ft.Text(f"${(total_pending + total_paid):.2f}", weight=ft.FontWeight.BOLD, size=16),
                                    ]),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ], spacing=10),
                            padding=15,
                        ),
                    )
                )
            page.update()

        def mark_fee_paid(record):
            """Mark a fee as paid."""
            if update_fee_status(record.id, "Paid"):
                show_snackbar(page, "Fee marked as paid!")
                load_fees_records()
            else:
                show_snackbar(page, "Error updating fee status!", True)

        def confirm_delete_fee(fee_id):
            """Show confirmation dialog for deleting fee."""
            def delete_confirmed(e):
                if delete_fee_record(fee_id):
                    show_snackbar(page, "Fee record deleted!")
                    load_fees_records()
                else:
                    show_snackbar(page, "Error deleting fee record!", True)
                dialog.open = False
                page.update()

            def cancel_delete(e):
                dialog.open = False
                page.update()

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirm Delete"),
                content=ft.Text("Are you sure you want to delete this fee record?"),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel_delete),
                    ft.TextButton("Delete", on_click=delete_confirmed, style=ft.ButtonStyle(
                        color=ft.Colors.RED_700,
                    )),
                ],
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        def save_fee(e):
            """Save a new fee record."""
            if self.selected_student_for_fees is None:
                show_snackbar(page, "Please select a student!", True)
                return

            if not amount_field.value or not due_date_field.value:
                show_snackbar(page, "Amount and Due Date are required!", True)
                return

            try:
                amount = float(amount_field.value)
                if amount <= 0:
                    show_snackbar(page, "Amount must be positive!", True)
                    return

                if add_fee_record(
                    self.selected_student_for_fees,
                    amount,
                    due_date_field.value,
                    description_field.value
                ):
                    show_snackbar(page, "Fee record added successfully!")
                    # Reset form
                    amount_field.value = ""
                    description_field.value = ""
                    due_date_field.value = str(date.today())
                    load_fees_records()
                else:
                    show_snackbar(page, "Error adding fee record!", True)
            except ValueError:
                show_snackbar(page, "Invalid amount value!", True)

        def open_calendar(e):
            """Open date picker dialog."""
            def handle_date_change(e):
                due_date_field.value = e.control.value.strftime("%Y-%m-%d")
                page.update()

            date_picker = ft.DatePicker(
                on_change=handle_date_change,
                first_date=date(2020, 1, 1),
                last_date=date(2030, 12, 31),
            )
            page.overlay.append(date_picker)
            page.update()
            date_picker.pick_date()

        # Make date field clickable to open calendar
        due_date_field.on_click = open_calendar

        # Initialize
        load_students()
        if student_dropdown.value:
            load_fees_records()

        # Build view
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text("Fees Management", size=24, weight=ft.FontWeight.BOLD),
                    padding=20,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Add Fee Record", size=16, weight=ft.FontWeight.W_500),
                        student_dropdown,
                        ft.Row([
                            amount_field,
                            due_date_field,
                        ], spacing=15),
                        description_field,
                        ft.ElevatedButton(
                            "Add Fee Record",
                            icon=ft.Icons.ADD,
                            on_click=save_fee,
                        ),
                    ], spacing=15),
                    padding=20,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Fee Records", size=16, weight=ft.FontWeight.W_500),
                        ft.Container(
                            content=fees_list,
                            expand=True,
                        ),
                    ], spacing=10),
                    padding=20,
                    expand=True,
                ),
            ], spacing=0, expand=True),
            expand=True,
        )


class FaceEnrolView:
    """Face enrollment view."""

    def create_view(self, page: ft.Page, current_user: str):
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
                show_snackbar(page, "Please select a student!", True)
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
                    show_snackbar(page, "Face enrolment failed!", True)
                else:
                    if FaceService().enrol_student(student_id, frames):
                        status_text.value = "Face enrolled successfully!"
                        show_snackbar(page, "Face enrolled successfully!")
                    else:
                        status_text.value = "Error: No face detected. Try again with better lighting."
                        show_snackbar(page, "Face enrolment failed!", True)

            except Exception as ex:
                status_text.value = f"Error: {str(ex)}"
                show_snackbar(page, "Face enrolment failed!", True)

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


class LiveAttendanceView:
    """Live face attendance view."""

    def __init__(self):
        self.students_present = set()
        self.attendance_date = str(date.today())
        self.is_running = False

    def create_view(self, page: ft.Page, current_user: str):
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

        def start_live_attendance(e):
            """Start live attendance recognition."""
            nonlocal is_running, students_present
            is_running = True
            students_present = set()
            start_btn.disabled = True
            stop_btn.disabled = False
            status_text.value = "Live attendance running... Students detected will be marked present."
            page.update()

            def capture_loop():
                """Capture loop for live attendance."""
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
            """Stop live attendance and save results."""
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
            show_snackbar(page, f"Marked {marked_count} student(s) present")
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
