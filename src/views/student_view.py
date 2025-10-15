import flet as ft
from datetime import date
from typing import List, Optional
from utils import export_students_to_csv
from database import get_all_batches, add_batch, get_all_classes, add_class, get_all_students, add_student, update_student, delete_student
from models import Batch
from models import Student, Class


def create_student_view(page: ft.Page, show_snackbar, current_view, edit_student_id, open_attendance_for_student, open_fees_for_student):
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

    batch_dropdown = ft.Dropdown(
        label="Batch",
        hint_text="Select batch",
        # No icon for dropdown in 0.28.3
        width=200,
    )

    class_dropdown = ft.Dropdown(
        label="Class",
        hint_text="Select class",
        # No icon for dropdown in 0.28.3
        width=200,
    )

    search_field = ft.TextField(
        label="Search",
        hint_text="Search by name, batch, or class",
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda e: update_student_list(),
        expand=True,
    )

    student_list_view = ft.ListView(
        spacing=10,
        padding=20,
        expand=True,
    )

    def load_batches():
        """Load batches and classes into dropdowns."""
        batches = get_all_batches()
        classes = get_all_classes()
        batch_dropdown.options = [
            ft.dropdown.Option(key=str(b.id), text=b.name) for b in batches
        ]
        class_dropdown.options = [
            ft.dropdown.Option(key=str(c.id), text=c.name) for c in classes
        ]
        if batches:
            batch_dropdown.value = str(batches[0].id)
        if classes:
            class_dropdown.value = str(classes[0].id)

    def update_student_list():
        """Update the student list display."""
        students = get_all_students(search_field.value or "")
        student_list_view.controls.clear()

        if not students:
            student_list_view.controls.append(
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
                batch_text = student.batch_name or "No batch"
                student_list_view.controls.append(
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
                                        ft.Text(f"Batch {batch_text}", size=12, color=ft.Colors.GREY_600),
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
                                        on_click=lambda e, s=student: edit_student(s),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.CALENDAR_TODAY,
                                        icon_color=ft.Colors.GREEN_700,
                                        tooltip="Attendance",
                                        on_click=lambda e, s=student: open_attendance_for_student(s),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.PAYMENTS,
                                        icon_color=ft.Colors.ORANGE_700,
                                        tooltip="Fees",
                                        on_click=lambda e, s=student: open_fees_for_student(s),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED_700,
                                        tooltip="Delete",
                                        on_click=lambda e, sid=student.id: confirm_delete_student(sid),
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
        edit_student_id = student.id
        name_field.value = student.name
        age_field.value = str(student.age)
        batch_dropdown.value = str(student.batch_id) if student.batch_id else None
        class_dropdown.value = str(student.class_id) if student.class_id else None
        page.update()

    def clear_form():
        """Clear all form fields."""
        edit_student_id = None
        name_field.value = ""
        age_field.value = ""
        load_batches()
        page.update()

    def save_student(e):
        """Save or update student."""
        if not name_field.value or not age_field.value or not batch_dropdown.value:
            show_snackbar("All fields are required!", True)
            return

        try:
            age = int(age_field.value)
            if age < 5 or age > 18:
                show_snackbar("Age must be between 5 and 18!", True)
                return

            batch_id = int(batch_dropdown.value) if batch_dropdown.value else None
            class_id = int(class_dropdown.value) if class_dropdown.value else None

            if edit_student_id is None:
                if add_student(name_field.value, age, batch_id, class_id):
                    show_snackbar("Student added successfully!")
                    clear_form()
                    update_student_list()
                else:
                    show_snackbar("Error adding student!", True)
            else:
                if update_student(edit_student_id, name_field.value, age,
                                batch_id, class_id):
                    show_snackbar("Student updated successfully!")
                    clear_form()
                    update_student_list()
                else:
                    show_snackbar("Error updating student!", True)
        except ValueError:
            show_snackbar("Invalid age value!", True)

    def confirm_delete_student(student_id: int):
        """Show confirmation dialog for deleting student."""
        def delete_confirmed(e):
            if delete_student(student_id):
                show_snackbar("Student deleted successfully!")
                update_student_list()
            else:
                show_snackbar("Error deleting student!", True)
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
            show_snackbar(f"Exported to: {filename}")
        except Exception as ex:
            show_snackbar(f"Export failed: {str(ex)}", True)

    def add_batch_dialog(e):
        """Show dialog to add new batch."""
        batch_name_field = ft.TextField(
            label="Batch Name",
            hint_text="e.g., 2024-2025",
            autofocus=True,
        )

        def save_batch(e):
            if batch_name_field.value and add_batch(batch_name_field.value):
                load_batches()
                show_snackbar("Batch added successfully!")
                dialog.open = False
                page.update()
            else:
                show_snackbar("Error adding batch! Name might be duplicate.", True)

        def close_dialog(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add New Batch"),
            content=ft.Container(
                content=batch_name_field,
                width=300,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.TextButton("Add", on_click=save_batch),
            ],
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def add_class_dialog(e):
        """Show dialog to add new class."""
        class_name_field = ft.TextField(
            label="Class Name",
            hint_text="e.g., Grade 10A",
            autofocus=True,
        )

        def save_class(e):
            if class_name_field.value and add_class(class_name_field.value):
                load_batches()
                show_snackbar("Class added successfully!")
                dialog.open = False
                page.update()
            else:
                show_snackbar("Error adding class! Name might be duplicate.", True)

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
    load_batches()
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
                        batch_dropdown,
                        class_dropdown,
                        ft.IconButton(
                            icon=ft.Icons.ADD_CIRCLE,
                            icon_color=ft.Colors.BLUE_700,
                            tooltip="Add New Batch",
                            on_click=add_batch_dialog,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.ADD_CIRCLE,
                            icon_color=ft.Colors.GREEN_700,
                            tooltip="Add New Class",
                            on_click=add_class_dialog,
                        ),
                    ]),
                    ft.Row([
                        ft.ElevatedButton(
                            "Save Student" if edit_student_id is None else "Update Student",
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
                        content=student_list_view,
                        expand=True,
                    ),
                ], spacing=10),
                padding=20,
                expand=True,
            ),
        ], spacing=0, expand=True),
        expand=True,
    )
