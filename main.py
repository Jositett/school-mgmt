"""
Main application entry point for School Management System
"""
import flet as ft

from database import init_db, authenticate_user
from views import (
    StudentView, AttendanceView, FeesView, FaceEnrolView, LiveAttendanceView
)
from utils import show_snackbar


def main(page: ft.Page):
    """Main application entry point."""
    # Configure page
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.title = "School Management System"
    page.window.width = 1200
    page.window.height = 800
    page.window.min_width = 800
    page.window.min_height = 600
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    # Modern color scheme
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.BLUE,
        use_material3=True,
    )

    # State variables
    current_user = None
    current_view = "students"
    selected_student_for_attendance = None
    selected_student_for_fees = None

    # View instances
    student_view = StudentView()
    attendance_view = AttendanceView()
    fees_view = FeesView()
    face_enrol_view = FaceEnrolView()
    live_attendance_view = LiveAttendanceView()

    def logout(e):
        """Logout current user."""
        nonlocal current_user
        current_user = None
        show_login()

    def create_app_bar():
        """Create modern app bar."""
        return ft.AppBar(
            title=ft.Text("School Management System", weight=ft.FontWeight.BOLD),
            center_title=False,
            bgcolor=ft.Colors.BLUE_700,
            actions=[
                ft.PopupMenuButton(
                    items=[
                        ft.PopupMenuItem(
                            text=f"Logged in as: {current_user}",
                            disabled=True,
                        ),
                        ft.PopupMenuItem(),
                        ft.PopupMenuItem(
                            text="Logout",
                            icon=ft.Icons.LOGOUT,
                            on_click=logout,
                        ),
                    ],
                    icon=ft.Icons.ACCOUNT_CIRCLE,
                    icon_color=ft.Colors.WHITE,
                ),
            ],
        )

    def create_navigation_rail():
        """Create modern navigation rail."""
        return ft.NavigationRail(
            selected_index={
                "students": 0,
                "enrol_face": 1,
                "live_attendance": 2,
                "attendance": 3,
                "fees": 4,
            }.get(current_view, 0),
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.PEOPLE_OUTLINE,
                    selected_icon=ft.Icons.PEOPLE,
                    label="Students",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PHOTO_CAMERA_OUTLINED,
                    selected_icon=ft.Icons.PHOTO_CAMERA,
                    label="Enrol Face",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.FACE_OUTLINED,
                    selected_icon=ft.Icons.FACE,
                    label="Live Attendance",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.EVENT_AVAILABLE_OUTLINED,
                    selected_icon=ft.Icons.EVENT_AVAILABLE,
                    label="Attendance",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PAYMENTS_OUTLINED,
                    selected_icon=ft.Icons.PAYMENTS,
                    label="Fees",
                ),
            ],
            on_change=lambda e: change_view(e.control.selected_index),
        )

    def change_view(index: int):
        """Change the current view based on navigation selection."""
        nonlocal current_view
        view_map = {
            0: "students",
            1: "enrol_face",
            2: "live_attendance",
            3: "attendance",
            4: "fees",
        }
        current_view = view_map.get(index, "students")
        show_main_app()

    def show_main_app():
        """Show the main application interface."""
        page.controls.clear()

        # Get the appropriate view
        view_content = None
        if current_view == "students":
            view_content = student_view.create_view(page, current_user)
        elif current_view == "enrol_face":
            view_content = face_enrol_view.create_view(page, current_user)
        elif current_view == "live_attendance":
            view_content = live_attendance_view.create_view(page, current_user)
        elif current_view == "attendance":
            view_content = attendance_view.create_view(page, current_user)
        elif current_view == "fees":
            view_content = fees_view.create_view(page, current_user)

        # Create main layout
        page.add(
            create_app_bar(),
            ft.Row([
                create_navigation_rail(),
                ft.VerticalDivider(width=1),
                ft.Container(
                    content=view_content,
                    expand=True,
                ),
            ], expand=True)
        )
        page.update()

    def show_login():
        """Show login screen."""
        page.controls.clear()

        # Use prefix_icon (works in 0.28.3 despite deprecation warning)
        username_field = ft.TextField(
            label="Username",
            prefix_icon=ft.Icons.PERSON,
            width=300,
            autofocus=True,
        )

        password_field = ft.TextField(
            label="Password",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            width=300,
        )

        def handle_login(e):
            nonlocal current_user
            if authenticate_user(username_field.value or "", password_field.value or ""):
                current_user = username_field.value
                show_main_app()
            else:
                show_snackbar(page, "Invalid username or password!", True)

        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Image(
                        src="https://cdn-icons-png.flaticon.com/512/2966/2966307.png",
                        width=100,
                        height=100,
                    ),
                    ft.Text("School Management System", size=24, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=20),
                    username_field,
                    password_field,
                    ft.ElevatedButton(
                        "Login",
                        icon=ft.Icons.LOGIN,
                        width=300,
                        on_click=handle_login,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                alignment=ft.alignment.center,
                expand=True,
            )
        )
        page.update()

    # Initialize database and show login
    init_db()
    show_login()


if __name__ == "__main__":
    ft.app(target=main)
