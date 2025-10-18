"""
Face encodings management section for admin view.

This module provides the face encodings management interface with CRUD operations.
"""

import flet as ft
import sqlite3
import os


def create_face_encodings_section(page: ft.Page, show_snackbar):
    """Create face encodings management section."""

    # Section-specific search
    search_field = ft.TextField(
        label="Search face encodings",
        hint_text="Search by student name or ID",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        on_change=lambda e: update_encoding_list(),
    )

    encoding_list_view = ft.ListView(spacing=10, padding=20, expand=True)

    def update_encoding_list():
        """Update the face encoding list display."""
        query = search_field.value or ""

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

            if query:
                encodings = [e for e in encodings if query.lower() in (e[1] or f"Student {e[0]}").lower()]

            encoding_list_view.controls.clear()

            if not encodings:
                encoding_list_view.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.GREY_400),
                            ft.Text("No face encodings found", size=16, color=ft.Colors.GREY_600),
                            ft.Text("Face encodings are created during face enrollment", size=12, color=ft.Colors.GREY_500),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=40,
                    )
                )
            else:
                for encoding in encodings:
                    student_id, student_name, updated_at = encoding
                    student_name = student_name or f"Student {student_id}"

                    encoding_list_view.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.CircleAvatar(
                                            content=ft.Text(student_name[0].upper(), size=20, weight=ft.FontWeight.BOLD),
                                            bgcolor=ft.Colors.PURPLE_200,
                                            color=ft.Colors.PURPLE_900,
                                        ),
                                        width=50,
                                    ),
                                    ft.Column([
                                        ft.Text(student_name, weight=ft.FontWeight.BOLD, size=16),
                                        ft.Row([
                                            ft.Icon(ft.Icons.NUMBERS, size=14, color=ft.Colors.GREY_600),
                                            ft.Text(f"ID: {student_id}", size=12, color=ft.Colors.GREY_600),
                                            ft.VerticalDivider(width=1),
                                            ft.Icon(ft.Icons.UPDATE, size=14, color=ft.Colors.GREY_600),
                                            ft.Text(f"Updated: {updated_at or 'Unknown'}", size=12, color=ft.Colors.GREY_600),
                                        ], spacing=5),
                                    ], spacing=5, expand=True),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED_700,
                                        tooltip="Delete Encoding",
                                        on_click=lambda e, sid=student_id, sname=student_name: confirm_delete_encoding(sid, sname),
                                    ),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                padding=15,
                            ),
                        )
                    )
        except Exception as ex:
            encoding_list_view.controls.clear()
            encoding_list_view.controls.append(
                ft.Container(
                    content=ft.Text(f"Error loading face encodings: {ex}", color=ft.Colors.RED_600),
                    alignment=ft.alignment.center,
                    padding=40,
                )
            )
        page.update()

    def confirm_delete_encoding(student_id, student_name):
        """Show confirmation dialog for deleting face encoding."""
        def delete_confirmed(e):
            try:
                conn = sqlite3.connect("school.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM face_encodings WHERE student_id = ?", (student_id,))
                conn.commit()
                conn.close()
                show_snackbar(f"Face encoding deleted for {student_name}!")
                update_encoding_list()
            except Exception as ex:
                show_snackbar(f"Error deleting encoding: {ex}", True)
            dialog.open = False
            page.update()

        def cancel_delete(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete the face encoding for '{student_name}'?\nThis action cannot be undone."),
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

    # Initialize
    update_encoding_list()

    # Build section
    return ft.Container(
        content=ft.Column([
            ft.Text("Face Encodings", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_700),
            ft.Text("Manage student face recognition data", size=12, color=ft.Colors.GREY_600),
            ft.Divider(),
            search_field,
            ft.Divider(),
            ft.Container(
                content=ft.Column([
                    ft.Text("Face Encodings List", size=14, weight=ft.FontWeight.W_500),
                    ft.Container(content=encoding_list_view, expand=True),
                    ft.Text("Note: Face encodings are automatically created during face enrollment.", size=12, color=ft.Colors.GREY_600, italic=True),
                ], spacing=10),
                expand=True,
            ),
        ], spacing=15),
        padding=20,
    )