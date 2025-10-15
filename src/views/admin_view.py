"""
Admin management view for database CRUD operations.

This view provides interfaces for managing batches, classes, users, and face encodings.
"""

import flet as ft
from database import (
    get_all_batches, add_batch, get_all_classes, add_class,
    get_all_students, get_student_by_id, authenticate_user
)
import sqlite3
import os


def create_admin_view(page: ft.Page, show_snackbar):
    """Create modern admin management view with improved UX."""

    # Get responsive layout info
    window_width = getattr(page.window, 'width', 800)

    # Statistics cards
    def get_stats_cards():
        """Get statistics overview cards."""
        try:
            from database import get_all_students, get_all_batches, get_all_classes
            total_students = len(get_all_students())
            total_batches = len(get_all_batches())
            total_classes = len(get_all_classes())

            # Get face encodings count
            conn = sqlite3.connect("school.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM face_encodings")
            total_encodings = cursor.fetchone()[0]
            conn.close()

            return ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Icon(ft.Icons.PEOPLE, size=40, color=ft.Colors.BLUE_600),
                                    ft.Text("Students", size=14, weight=ft.FontWeight.BOLD),
                                    ft.Text(str(total_students), size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600),
                                ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                                padding=20,
                            ),
                            elevation=2,
                        ),
                        width=200 if window_width > 800 else None,
                        expand=window_width <= 800,
                    ),
                    ft.Container(
                        content=ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Icon(ft.Icons.SCHOOL, size=40, color=ft.Colors.GREEN_600),
                                    ft.Text("Classes", size=14, weight=ft.FontWeight.BOLD),
                                    ft.Text(str(total_classes), size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_600),
                                ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                                padding=20,
                            ),
                            elevation=2,
                        ),
                        width=200 if window_width > 800 else None,
                        expand=window_width <= 800,
                    ),
                    ft.Container(
                        content=ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Icon(ft.Icons.SCHOOL, size=40, color=ft.Colors.ORANGE_600),
                                    ft.Text("Batches", size=14, weight=ft.FontWeight.BOLD),
                                    ft.Text(str(total_batches), size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_600),
                                ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                                padding=20,
                            ),
                            elevation=2,
                        ),
                        width=200 if window_width > 800 else None,
                        expand=window_width <= 800,
                    ),
                    ft.Container(
                        content=ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Icon(ft.Icons.FACE, size=40, color=ft.Colors.PURPLE_600),
                                    ft.Text("Face Data", size=14, weight=ft.FontWeight.BOLD),
                                    ft.Text(str(total_encodings), size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_600),
                                ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                                padding=20,
                            ),
                            elevation=2,
                        ),
                        width=200 if window_width > 800 else None,
                        expand=window_width <= 800,
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
                margin=ft.margin.only(top=20, bottom=10),
            )
        except:
            return ft.Container()  # Return empty container on error

    def get_batches_tab():
        """Create modern batches management tab."""
        batches_list = ft.Column(spacing=10)

        # Search and add controls
        search_field = ft.TextField(
            label="Search batches...",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=lambda e: filter_batches(e.control.value),
        )

        add_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            bgcolor=ft.Colors.BLUE_600,
            on_click=lambda e: show_add_batch_dialog(),
        )

        def filter_batches(query=None):
            """Filter batches based on search query."""
            from database import get_all_batches
            batches = get_all_batches()
            if query:
                batches = [b for b in batches if query.lower() in b.name.lower()]
            refresh_batches_list(batches)

        def refresh_batches_list(batches):
            """Refresh the batches card list."""
            batches_list.controls.clear()

            if not batches:
                batches_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.GREY_300),
                            ft.Text("No batches found", size=16, color=ft.Colors.GREY_600),
                            ft.Text("Click + to add your first batch", size=12, color=ft.Colors.GREY_500),
                        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                        alignment=ft.alignment.center,
                        height=300,
                    )
                )
            else:
                for batch in batches:
                    # Count students in this batch
                    students_count = len([s for s in get_all_students() if s.batch_id == batch.id])

                    card = ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(
                                        content=ft.Icon(ft.Icons.SCHOOL, size=32, color=ft.Colors.ORANGE_600),
                                        margin=ft.margin.only(right=15),
                                    ),
                                    ft.Column([
                                        ft.Text(batch.name, size=18, weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{students_count} students", size=12, color=ft.Colors.GREY_600),
                                        ft.Text(f"{batch.start_time} - {batch.end_time}", size=12, color=ft.Colors.BLUE_600),
                                    ], expand=True, spacing=2),
                                    ft.PopupMenuButton(
                                        items=[
                                            ft.PopupMenuItem(
                                                text="Edit",
                                                icon=ft.Icons.EDIT,
                                                on_click=lambda e, b=batch: edit_batch(b),
                                            ),
                                            ft.PopupMenuItem(
                                                text="Delete",
                                                icon=ft.Icons.DELETE,
                                                on_click=lambda e, b=batch: delete_batch(b),
                                            ),
                                        ],
                                        icon=ft.Icons.MORE_VERT,
                                    ),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ], spacing=10),
                            padding=20,
                        ),
                        elevation=1,
                        margin=ft.margin.only(bottom=8),
                    )
                    batches_list.controls.append(card)

            page.update()

        def show_add_batch_dialog():
            """Show modern add batch dialog."""
            batch_name_field = ft.TextField(
                label="Batch Name",
                hint_text="e.g., 2025-2026 Morning",
                autofocus=True,
            )
            start_time_field = ft.TextField(
                label="Start Time",
                hint_text="HH:MM",
                value="09:00",
                width=120,
            )
            end_time_field = ft.TextField(
                label="End Time",
                hint_text="HH:MM",
                value="17:00",
                width=120,
            )

            def save_batch(e):
                name = batch_name_field.value
                start_time = start_time_field.value
                end_time = end_time_field.value

                if not name or not start_time or not end_time:
                    show_snackbar("Batch name, start time, and end time are required!", True)
                    return

                from database import add_batch
                if add_batch(name, start_time, end_time):
                    filter_batches(search_field.value)
                    show_snackbar(f"✓ Batch '{name}' added!")
                    dlg.open = False
                    page.update()
                else:
                    show_snackbar("Failed to add batch!", True)

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Add New Batch"),
                content=ft.Container(
                    content=ft.Column([
                        batch_name_field,
                        ft.Row([
                            start_time_field,
                            end_time_field,
                        ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                    ], spacing=15, tight=True),
                    width=400,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: page.close(dlg)),
                    ft.ElevatedButton("Add Batch", on_click=save_batch, style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        def edit_batch(batch):
            """Edit batch with dialog."""
            show_snackbar(f"Edit feature for '{batch.name}' coming soon!", False)

        def delete_batch(batch):
            """Delete batch with confirmation."""
            def confirm_delete(e):
                try:
                    conn = sqlite3.connect("school.db")
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM batches WHERE id = ?", (batch.id,))
                    conn.commit()
                    conn.close()
                    filter_batches(search_field.value)
                    show_snackbar(f"✓ '{batch.name}' deleted!")
                except Exception as ex:
                    show_snackbar(f"Failed to delete batch: {ex}", True)

            # Check if batch is in use
            students_using = len([s for s in get_all_students() if s.batch_id == batch.id])
            if students_using > 0:
                show_snackbar(f"Cannot delete: {students_using} students are in this batch!", True)
                return

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Delete Batch"),
                content=ft.Text(f"Are you sure you want to delete '{batch.name}'?\nThis action cannot be undone."),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: page.close(dlg)),
                    ft.TextButton("Delete", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED_600)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.open(dlg)

        # Initial load
        filter_batches()

        return ft.Container(
            content=ft.Column([
                ft.Text("Batch Management", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_700),
                ft.Text("Manage class batches and schedules", size=14, color=ft.Colors.GREY_600),
                ft.Divider(height=20),
                search_field,
                ft.Container(
                    content=ft.Column([
                        batches_list,
                    ], scroll=ft.ScrollMode.AUTO, height=400),
                    padding=ft.padding.symmetric(vertical=10),
                ),
            ], spacing=15),
            alignment=ft.alignment.top_left,
        ), add_button

    def get_classes_tab():
        """Create classes management tab."""
        classes_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Name")),
                ft.DataColumn(ft.Text("Actions")),
            ],
            rows=[],
        )
        # Ensure rows is always a list
        if classes_table.rows is None:
            classes_table.rows = []

        name_field = ft.TextField(label="Class Name", width=200)

        def refresh_classes():
            """Refresh classes table."""
            from database import get_all_classes
            classes = get_all_classes()
            # Ensure rows is a list
            if not hasattr(classes_table, 'rows') or classes_table.rows is None:
                classes_table.rows = []
            else:
                classes_table.rows.clear()

            for cls in classes:
                classes_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(cls.id))),
                            ft.DataCell(ft.Text(cls.name)),
                            ft.DataCell(
                                ft.Row([
                                    ft.IconButton(
                                        ft.Icons.EDIT,
                                        icon_color=ft.Colors.BLUE,
                                        tooltip="Edit class",
                                        on_click=lambda e, c=cls: edit_class(c),
                                    ),
                                    ft.IconButton(
                                        ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED,
                                        tooltip="Delete class",
                                        on_click=lambda e, c=cls: delete_class(c),
                                    ),
                                ])
                            ),
                        ]
                    )
                )
            page.update()

        def add_new_class(e):
            """Add new class."""
            name = name_field.value

            if not name:
                show_snackbar("Class name is required!", True)
                return

            from database import add_class
            if add_class(name):
                name_field.value = ""
                refresh_classes()
                show_snackbar("Class added successfully!")
            else:
                show_snackbar("Failed to add class!", True)

        def edit_class(cls):
            """Edit class."""
            show_snackbar(f"Edit class: {cls.name} (Feature to be implemented)", True)

        def delete_class(cls):
            """Delete class."""
            def confirm_delete(e):
                try:
                    conn = sqlite3.connect("school.db")
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM classes WHERE id = ?", (cls.id,))
                    conn.commit()
                    conn.close()
                    refresh_classes()
                    show_snackbar("Class deleted successfully!")
                except Exception as ex:
                    show_snackbar(f"Failed to delete class: {ex}", True)

            # Check if class is in use
            students_using = len([s for s in get_all_students() if s.class_id == cls.id])
            if students_using > 0:
                show_snackbar(f"Cannot delete class: {students_using} students are assigned to it!", True)
                return

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirm Delete"),
                content=ft.Text(f"Delete class '{cls.name}'?"),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: page.close(dlg)),
                    ft.TextButton("Delete", on_click=confirm_delete),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.open(dlg)

        refresh_classes()  # Initial load

        return ft.Container(
            content=ft.Column([
                ft.Text("Class Management", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row([
                    name_field,
                    ft.ElevatedButton("Add Class", on_click=add_new_class),
                ], spacing=10),
                ft.Container(height=20),
                ft.Container(
                    content=classes_table,
                    height=400,
                    border=ft.border.all(1, ft.Colors.OUTLINE),
                    border_radius=10,
                    padding=10,
                ),
            ], spacing=15),
        )

    def get_users_tab():
        """Create users management tab."""
        users_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Username")),
                ft.DataColumn(ft.Text("Actions")),
            ],
            rows=[],
        )
        # Ensure rows is always a list
        if users_table.rows is None:
            users_table.rows = []

        username_field = ft.TextField(label="Username", width=200)
        password_field = ft.TextField(label="Password", width=200, password=True)

        def refresh_users():
            """Refresh users table."""
            conn = sqlite3.connect("school.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, username FROM users")
            users = cursor.fetchall()
            conn.close()

            # Ensure rows is a list
            if not hasattr(users_table, 'rows') or users_table.rows is None:
                users_table.rows = []
            else:
                users_table.rows.clear()

            for user in users:
                user_id, username = user
                users_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(user_id))),
                            ft.DataCell(ft.Text(username)),
                            ft.DataCell(
                                ft.Row([
                                    ft.IconButton(
                                        ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED,
                                        tooltip="Delete user",
                                        on_click=lambda e, uid=user_id, uname=username: delete_user(uid, uname),
                                    ),
                                ])
                            ),
                        ]
                    )
                )
            page.update()

        def add_new_user(e):
            """Add new user."""
            username = username_field.value
            password = password_field.value

            if not username or not password:
                show_snackbar("Username and password are required!", True)
                return

            try:
                conn = sqlite3.connect("school.db")
                cursor = conn.cursor()
                # Check if user exists
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                if cursor.fetchone():
                    show_snackbar("Username already exists!", True)
                    conn.close()
                    return

                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                conn.close()

                username_field.value = ""
                password_field.value = ""
                refresh_users()
                show_snackbar("User added successfully!")
            except Exception as ex:
                show_snackbar(f"Failed to add user: {ex}", True)

        def delete_user(user_id, username):
            """Delete user."""
            if username == "admin":
                show_snackbar("Cannot delete admin user!", True)
                return

            def confirm_delete(e):
                try:
                    conn = sqlite3.connect("school.db")
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                    conn.commit()
                    conn.close()
                    refresh_users()
                    show_snackbar("User deleted successfully!")
                except Exception as ex:
                    show_snackbar(f"Failed to delete user: {ex}", True)

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirm Delete"),
                content=ft.Text(f"Delete user '{username}'?"),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: page.close(dlg)),
                    ft.TextButton("Delete", on_click=confirm_delete),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.open(dlg)

        refresh_users()  # Initial load

        return ft.Container(
            content=ft.Column([
                ft.Text("User Management", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row([
                    username_field,
                    password_field,
                    ft.ElevatedButton("Add User", on_click=add_new_user),
                ], spacing=10),
                ft.Container(height=20),
                ft.Container(
                    content=users_table,
                    height=400,
                    border=ft.border.all(1, ft.Colors.OUTLINE),
                    border_radius=10,
                    padding=10,
                ),
            ], spacing=15),
        )

    def get_face_encodings_tab():
        """Create face encodings management tab."""
        encodings_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Student ID")),
                ft.DataColumn(ft.Text("Student Name")),
                ft.DataColumn(ft.Text("Updated At")),
                ft.DataColumn(ft.Text("Actions")),
            ],
            rows=[],
        )
        # Ensure rows is always a list
        if encodings_table.rows is None:
            encodings_table.rows = []

        def refresh_encodings():
            """Refresh face encodings table."""
            try:
                conn = sqlite3.connect("school.db")
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT fe.student_id, s.name, fe.updated_at
                    FROM face_encodings fe
                    LEFT JOIN students s ON fe.student_id = s.id
                    ORDER BY fe.updated_at DESC
                """)
                encodings = cursor.fetchall()
                conn.close()

                # Ensure rows is a list
                if not hasattr(encodings_table, 'rows') or encodings_table.rows is None:
                    encodings_table.rows = []
                else:
                    encodings_table.rows.clear()

                for encoding in encodings:
                    student_id, student_name, updated_at = encoding
                    student_name = student_name or f"Student {student_id}"

                    encodings_table.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(str(student_id))),
                                ft.DataCell(ft.Text(student_name)),
                                ft.DataCell(ft.Text(updated_at or "Unknown")),
                                ft.DataCell(
                                    ft.IconButton(
                                        ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED,
                                        tooltip="Delete encoding",
                                        on_click=lambda e, sid=student_id, sname=student_name: delete_encoding(sid, sname),
                                    )
                                ),
                            ]
                        )
                    )
                page.update()
            except Exception as ex:
                show_snackbar(f"Failed to load face encodings: {ex}", True)

        def delete_encoding(student_id, student_name):
            """Delete face encoding."""
            def confirm_delete(e):
                try:
                    conn = sqlite3.connect("school.db")
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM face_encodings WHERE student_id = ?", (student_id,))
                    conn.commit()
                    conn.close()
                    refresh_encodings()
                    show_snackbar(f"Face encoding deleted for {student_name}!")
                except Exception as ex:
                    show_snackbar(f"Failed to delete encoding: {ex}", True)

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirm Delete"),
                content=ft.Text(f"Delete face encoding for '{student_name}'?"),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: page.close(dlg)),
                    ft.TextButton("Delete", on_click=confirm_delete),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.open(dlg)

        refresh_encodings()  # Initial load

        return ft.Container(
            content=ft.Column([
                ft.Text("Face Encodings Management", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Container(height=20),
                ft.Container(
                    content=encodings_table,
                    height=400,
                    border=ft.border.all(1, ft.Colors.OUTLINE),
                    border_radius=10,
                    padding=10,
                ),
                ft.Container(height=10),
                ft.Text("Note: Face encodings are automatically created during face enrollment.", size=12, color=ft.Colors.GREY),
            ], spacing=15),
        )

    # Create tabs
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(
                text="Batches",
                content=get_batches_tab()[0],  # Get content only
            ),
            ft.Tab(
                text="Classes",
                content=get_classes_tab(),
            ),
            ft.Tab(
                text="Users",
                content=get_users_tab(),
            ),
            ft.Tab(
                text="Face Encodings",
                content=get_face_encodings_tab(),
            ),
        ],
        expand=True,
    )

    # Add floating action button to page overlay
    add_fab = get_batches_tab()[1]  # Get the FAB
    page.overlay.append(add_fab)

    return ft.Container(
        content=ft.Column([
            get_stats_cards(),  # Add statistics at the top
            ft.Container(
                content=tabs,
                padding=20,
                expand=True,
            ),
        ], spacing=0, expand=True),
        expand=True,
    )
