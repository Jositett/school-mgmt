"""
Class management section for admin view.

This module provides the classes management interface with CRUD operations.
"""

import flet as ft
import sqlite3
from database import get_all_classes, add_class, get_all_students
from sections.admin_ui_components import create_day_selector, create_date_range_picker


# Utility functions for class scheduling display
def get_days_from_bitmask(bitmask):
    """Convert bitmask to readable day names."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_bits = [1, 2, 4, 8, 16, 32, 64]

    if bitmask == 127:  # All days
        return "Daily"
    elif bitmask == 31:  # Mon-Fri
        return "Mon-Fri"
    elif bitmask == 96:  # Sat-Sun
        return "Sat-Sun"
    elif bitmask == 0:
        return "No days"

    selected_days = []
    for i, bit in enumerate(day_bits):
        if bitmask & bit:
            selected_days.append(days[i])

    return ", ".join(selected_days)


def format_date_range(start_date, end_date):
    """Format date range for display."""
    if not start_date and not end_date:
        return ""

    if start_date and end_date:
        return f"{start_date} to {end_date}"
    elif start_date:
        return f"From {start_date}"
    elif end_date:
        return f"Until {end_date}"
    else:
        return ""


def ResponsiveCard(content, **kwargs):
    """Responsive Card component."""
    return ft.Card(
        content=ft.Container(content=content, padding=15),
        elevation=2,
        **kwargs
    )


def create_classes_section(page: ft.Page, show_snackbar):
    """Create classes management section."""

    # State variables
    edit_class_id = None

    # Day selector and date range picker components
    day_selector = create_day_selector(page)
    date_range_picker = create_date_range_picker(page)

    # Form fields
    class_name_field = ft.TextField(
        label="Class Name",
        hint_text="e.g., Grade 10A",
        prefix_icon=ft.Icons.CLASS_,
    )

    start_time_field = ft.TextField(
        label="Start Time",
        hint_text="HH:MM",
        prefix_icon=ft.Icons.SCHEDULE,
        value="09:00",
        width=120,
    )

    end_time_field = ft.TextField(
        label="End Time",
        hint_text="HH:MM",
        prefix_icon=ft.Icons.SCHEDULE,
        value="15:00",
        width=120,
    )

    # Section-specific search
    search_field = ft.TextField(
        label="Search classes",
        hint_text="Search by name",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        on_change=lambda e: update_class_list(),
    )

    class_list_view = ft.ListView(spacing=10, padding=20, expand=True)

    def update_class_list():
        """Update the class list display."""
        query = search_field.value or ""
        classes = get_all_classes()

        if query:
            classes = [c for c in classes if query.lower() in c.name.lower()]

        class_list_view.controls.clear()

        if not classes:
            class_list_view.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.GREY_400),
                        ft.Text("No classes found", size=16, color=ft.Colors.GREY_600),
                        ft.Text("Add your first class below", size=12, color=ft.Colors.GREY_500),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=40,
                )
            )
        else:
            for cls in classes:
                # Count students in this class
                students_count = len([s for s in get_all_students() if s.class_id == cls.id])

                # Prepare scheduling info row
                scheduling_info = []
                days_text = get_days_from_bitmask(cls.recurrence_pattern)
                date_range_text = format_date_range(cls.start_date, cls.end_date)

                if days_text and days_text != "Daily":
                    scheduling_info.extend([
                        ft.Icon(ft.Icons.CALENDAR_VIEW_WEEK, size=14, color=ft.Colors.BLUE_600),
                        ft.Text(days_text, size=12, color=ft.Colors.BLUE_600),
                    ])

                if date_range_text:
                    if scheduling_info:
                        scheduling_info.append(ft.VerticalDivider(width=1))
                    scheduling_info.extend([
                        ft.Icon(ft.Icons.DATE_RANGE, size=14, color=ft.Colors.BLUE_600),
                        ft.Text(date_range_text, size=12, color=ft.Colors.BLUE_600),
                    ])

                class_list_view.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row([
                                ft.Container(
                                    content=ft.CircleAvatar(
                                        content=ft.Text(cls.name[0].upper(), size=20, weight=ft.FontWeight.BOLD),
                                        bgcolor=ft.Colors.GREEN_200,
                                        color=ft.Colors.GREEN_900,
                                    ),
                                    width=50,
                                ),
                                ft.Column([
                                    ft.Text(cls.name, weight=ft.FontWeight.BOLD, size=16),
                                    ft.Row([
                                        ft.Icon(ft.Icons.PEOPLE, size=14, color=ft.Colors.GREY_600),
                                        ft.Text(f"{students_count} students", size=12, color=ft.Colors.GREY_600),
                                        ft.VerticalDivider(width=1),
                                        ft.Icon(ft.Icons.SCHEDULE, size=14, color=ft.Colors.GREY_600),
                                        ft.Text(f"{cls.start_time} - {cls.end_time}", size=12, color=ft.Colors.GREY_600),
                                    ], spacing=5),
                                    ft.Row(scheduling_info, spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER) if scheduling_info else ft.Container(),
                                ], spacing=5, expand=True),
                                ft.Row([
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        icon_color=ft.Colors.BLUE_700,
                                        tooltip="Edit",
                                        on_click=lambda e, c=cls: edit_class(c),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED_700,
                                        tooltip="Delete",
                                        on_click=lambda e, c=cls: confirm_delete_class(c),
                                    ),
                                ], spacing=0),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=15,
                        ),
                    )
                )
        page.update()

    def edit_class(cls):
        """Load class data for editing."""
        nonlocal edit_class_id
        edit_class_id = cls.id
        class_name_field.value = cls.name
        start_time_field.value = cls.start_time
        end_time_field.value = cls.end_time

        # Set scheduling values
        day_selector.set_bitmask(cls.recurrence_pattern or 127)
        date_range_picker.set_dates(cls.start_date, cls.end_date)

        page.update()

    def clear_class_form():
        """Clear class form fields."""
        nonlocal edit_class_id
        edit_class_id = None
        class_name_field.value = ""
        start_time_field.value = "09:00"
        end_time_field.value = "15:00"

        # Reset scheduling components to defaults
        day_selector.set_bitmask(127)  # Default to all days
        date_range_picker.clear_dates()  # Clear date ranges

        page.update()

    def save_class(e):
        """Save or update class."""
        if not class_name_field.value or not start_time_field.value or not end_time_field.value:
            show_snackbar("All fields are required!", True)
            return

        # Get scheduling values
        recurrence_pattern = day_selector.get_bitmask()
        start_date, end_date = date_range_picker.get_selected_dates()

        if edit_class_id is None:
            if add_class(class_name_field.value, start_time_field.value, end_time_field.value, start_date, end_date, recurrence_pattern):
                show_snackbar("Class added successfully!")
                clear_class_form()
                update_class_list()
            else:
                show_snackbar("Error adding class! Name may already exist.", True)
        else:
            # Check for duplicate name first
            try:
                conn = sqlite3.connect("school.db")
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM classes WHERE name = ? AND id != ?", (class_name_field.value, edit_class_id))
                if cursor.fetchone():
                    show_snackbar("Class name already exists!", True)
                    conn.close()
                    return
                cursor.execute("""
                    UPDATE classes SET name = ?, start_time = ?, end_time = ?, start_date = ?, end_date = ?, recurrence_pattern = ?
                    WHERE id = ?
                """, (class_name_field.value, start_time_field.value, end_time_field.value, start_date, end_date, recurrence_pattern, edit_class_id))
                if cursor.rowcount > 0:
                    conn.commit()
                    show_snackbar("Class updated successfully!")
                    clear_class_form()
                    update_class_list()
                else:
                    show_snackbar("Error updating class: Class not found!", True)
                conn.close()
            except Exception as ex:
                show_snackbar(f"Error updating class: {ex}", True)

    def confirm_delete_class(cls):
        """Show confirmation dialog for deleting class."""
        def delete_confirmed(e):
            try:
                # Check if class is in use
                students_using = len([s for s in get_all_students() if s.class_id == cls.id])
                if students_using > 0:
                    show_snackbar(f"Cannot delete: {students_using} students are in this class!", True)
                    return

                conn = sqlite3.connect("school.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM classes WHERE id = ?", (cls.id,))
                conn.commit()
                conn.close()
                show_snackbar("Class deleted successfully!")
                update_class_list()
            except Exception as ex:
                show_snackbar(f"Error deleting class: {ex}", True)
            dialog.open = False
            page.update()

        def cancel_delete(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete class '{cls.name}'?\nThis action cannot be undone."),
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

    def add_class_quick(e):
        """Quick add class dialog."""
        name_field = ft.TextField(label="Class Name", hint_text="e.g., Grade 10A", autofocus=True)
        start_field = ft.TextField(label="Start Time", value="09:00", width=100)
        end_field = ft.TextField(label="End Time", value="15:00", width=100)

        def save_quick(e):
            if name_field.value and start_field.value and end_field.value:
                if add_class(name_field.value, start_field.value, end_field.value):
                    update_class_list()
                    show_snackbar("Class added successfully!")
                    dlg.open = False
                    page.update()
                else:
                    show_snackbar("Error adding class! Name may already exist.", True)
            else:
                show_snackbar("All fields are required!", True)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add New Class"),
            content=ft.Container(
                content=ft.Column([
                    name_field,
                    ft.Row([start_field, end_field], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                ], spacing=15, tight=True),
                width=350,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: (setattr(dlg, 'open', False), page.update())),
                ft.ElevatedButton("Add Class", on_click=save_quick),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # Initialize
    update_class_list()

    # Build section
    return ft.Container(
        content=ft.Column([
            ft.Text("Class Management", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700),
            ft.Text("Manage student classes", size=12, color=ft.Colors.GREY_600),
            ft.Divider(),
            search_field,
            ft.Container(
                content=ft.Column([
                    ft.Text("Add / Edit Class", size=14, weight=ft.FontWeight.W_500),
                    ft.Row([
                        class_name_field,
                        start_time_field,
                        end_time_field,
                        ft.IconButton(
                            icon=ft.Icons.ADD_CIRCLE,
                            icon_color=ft.Colors.GREEN_700,
                            tooltip="Quick Add Class",
                            on_click=add_class_quick,
                        ),
                    ]),
                    day_selector,
                    date_range_picker,
                    ft.Row([
                        ft.ElevatedButton(
                            "Save Class" if edit_class_id is None else "Update Class",
                            icon=ft.Icons.SAVE,
                            on_click=save_class,
                        ),
                        ft.OutlinedButton(
                            "Clear",
                            icon=ft.Icons.CLEAR,
                            on_click=lambda e: clear_class_form(),
                        ),
                    ]),
                ], spacing=10),
                padding=15,
                border=ft.border.all(1, ft.Colors.OUTLINE),
                border_radius=10,
            ),
            ft.Divider(),
            ft.Container(
                content=ft.Column([
                    ft.Text("Classes List", size=14, weight=ft.FontWeight.W_500),
                    ft.Container(content=class_list_view, expand=True),
                ], spacing=10),
                expand=True,
            ),
        ], spacing=15),
        padding=20,
    )
