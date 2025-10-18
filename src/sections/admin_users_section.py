"""
User management section for admin view.
"""

import flet as ft
import sqlite3
import os


def create_users_section(page: ft.Page, show_snackbar):
    """Create users management section."""

    # State variables
    edit_user_id = None

    # Form fields
    username_field = ft.TextField(
        label="Username",
        hint_text="Enter username",
        prefix_icon=ft.Icons.PERSON,
        expand=True,
    )

    password_field = ft.TextField(
        label="Password",
        hint_text="Enter password",
        prefix_icon=ft.Icons.LOCK,
        password=True,
        expand=True,
    )

    # Section-specific search
    search_field = ft.TextField(
        label="Search users",
        hint_text="Search by username",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        on_change=lambda e: update_user_list(),
    )

    user_list_view = ft.ListView(spacing=10, padding=20, expand=True)

    def update_user_list():
        """Update the user list display."""
        query = search_field.value or global_search_query

        conn = sqlite3.connect("school.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users")
        users = cursor.fetchall()
        conn.close()

        if query:
            users = [u for u in users if query.lower() in u[1].lower()]

        user_list_view.controls.clear()

        if not users:
            user_list_view.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.GREY_400),
                        ft.Text("No users found", size=16, color=ft.Colors.GREY_600),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=40,
                )
            )
        else:
            for user in users:
                user_id, username = user
                role = "Admin" if username == "admin" else "User"

                user_list_view.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row([
                                ft.Container(
                                    content=ft.CircleAvatar(
                                        content=ft.Text(username[0].upper(), size=20, weight=ft.FontWeight.BOLD),
                                        bgcolor=ft.Colors.BLUE_200,
                                        color=ft.Colors.BLUE_900,
                                    ),
                                    width=50,
                                ),
                                ft.Column([
                                    ft.Text(username, weight=ft.FontWeight.BOLD, size=16),
                                    ft.Row([
                                        ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS if role == "Admin" else ft.Icons.PERSON, size=14, color=ft.Colors.GREY_600),
                                        ft.Text(role, size=12, color=ft.Colors.GREY_600),
                                    ], spacing=5),
                                ], spacing=5, expand=True),
                                ft.Row([
                                    ft.IconButton(
                                        icon=ft.Icons.LOCK_RESET,
                                        icon_color=ft.Colors.ORANGE_700,
                                        tooltip="Reset Password",
                                        on_click=lambda e, uid=user_id, uname=username: reset_user_password(uid, uname),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED_700,
                                        tooltip="Delete",
                                        on_click=lambda e, uid=user_id, uname=username: confirm_delete_user(uid, uname),
                                        disabled=username == "admin",
                                    ),
                                ], spacing=0),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=15,
                        ),
                    )
                )
        page.update()

    def edit_user(user):
        """Load user data for editing."""
        nonlocal edit_user_id
        edit_user_id = user[0]  # user_id
        username_field.value = user[1]  # username
        password_field.value = ""  # Don't show current password
        page.update()

    def clear_user_form():
        """Clear user form fields."""
        nonlocal edit_user_id
        edit_user_id = None
        username_field.value = ""
        password_field.value = ""
        page.update()

    def save_user(e):
        """Save or update user."""
        if not username_field.value or not password_field.value:
            show_snackbar("Username and password are required!", True)
            return

        try:
            conn = sqlite3.connect("school.db")
            cursor = conn.cursor()

            if edit_user_id is None:
                # Check for duplicate username
                cursor.execute("SELECT id FROM users WHERE username = ?", (username_field.value,))
                if cursor.fetchone():
                    show_snackbar("Username already exists!", True)
                    conn.close()
                    return

                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username_field.value, password_field.value))
                show_snackbar("User added successfully!")
            else:
                # Check for duplicate username (excluding current user)
                cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username_field.value, edit_user_id))
                if cursor.fetchone():
                    show_snackbar("Username already exists!", True)
                    conn.close()
                    return

                cursor.execute("UPDATE users SET username = ?, password = ? WHERE id = ?", (username_field.value, password_field.value, edit_user_id))
                show_snackbar("User updated successfully!")

            conn.commit()
            conn.close()
            clear_user_form()
            update_user_list()
        except Exception as ex:
            show_snackbar(f"Error saving user: {ex}", True)

    def reset_user_password(user_id, username):
        """Reset user password."""
        if username == "admin":
            show_snackbar("Cannot reset admin password!", True)
            return

        new_password_field = ft.TextField(
            label="New Password",
            password=True,
            autofocus=True,
        )

        def save_new_password(e):
            if not new_password_field.value:
                show_snackbar("Password is required!", True)
                return

            try:
                conn = sqlite3.connect("school.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_password_field.value, user_id))
                conn.commit()
                conn.close()
                show_snackbar(f"Password reset for '{username}'!")
                dlg.open = False
                page.update()
            except Exception as ex:
                show_snackbar(f"Failed to reset password: {ex}", True)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Reset Password"),
            content=ft.Container(content=new_password_field, width=300),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: (setattr(dlg, 'open', False), page.update())),
                ft.ElevatedButton("Reset Password", on_click=save_new_password, style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_600)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def confirm_delete_user(user_id, username):
        """Show confirmation dialog for deleting user."""
        if username == "admin":
            show_snackbar("Cannot delete admin user!", True)
            return

        def delete_confirmed(e):
            try:
                conn = sqlite3.connect("school.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()
                show_snackbar("User deleted successfully!")
                update_user_list()
            except Exception as ex:
                show_snackbar(f"Error deleting user: {ex}", True)
            dialog.open = False
            page.update()

        def cancel_delete(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete user '{username}'?\nThis action cannot be undone."),
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
    update_user_list()

    # Build section
    return ft.Container(
        content=ft.Column([
            ft.Text("User Management", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
            ft.Text("Manage system users and permissions", size=12, color=ft.Colors.GREY_600),
            ft.Divider(),
            search_field,
            ft.Container(
                content=ft.Column([
                    ft.Text("Add / Edit User", size=14, weight=ft.FontWeight.W_500),
                    ft.Row([
                        username_field,
                    ]),
                    ft.Row([
                        password_field,
                    ]),
                    ft.Row([
                        ft.ElevatedButton(
                            "Save User" if edit_user_id is None else "Update User",
                            icon=ft.Icons.SAVE,
                            on_click=save_user,
                        ),
                        ft.OutlinedButton(
                            "Clear",
                            icon=ft.Icons.CLEAR,
                            on_click=lambda e: clear_user_form(),
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
                    ft.Text("Users List", size=14, weight=ft.FontWeight.W_500),
                    ft.Container(content=user_list_view, expand=True),
                ], spacing=10),
                expand=True,
            ),
        ], spacing=15),
        padding=20,
    )


# Global search support - this will be called from the main admin view
global_search_query = ""

def set_global_search_query(query):
    """Set the global search query for this section."""
    global global_search_query
    global_search_query = query or ""