"""
Main entry point for the School Management System.

This file replaces the main function in school_system.py and imports UI views from the views module.
"""

import flet as ft
from views import (
    create_student_view,
    create_attendance_view,
    create_fees_view,
    create_enrol_face_view,
    create_live_attendance_view,
    create_admin_view,
)
from database import authenticate_user, init_db, get_all_students
from models import *
from face_service import FaceService
from utils import export_students_to_csv

# Initialize FaceService singleton
face_service = FaceService()


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
    edit_student_id_container = [None]  # Use list to make it mutable
    current_view = "admin"
    selected_student_for_attendance = None
    selected_student_for_fees = None

    def show_snackbar(message: str, is_error: bool = False):
        """Show snackbar notification."""
        snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.RED_400 if is_error else ft.Colors.GREEN_400,
        )
        snack_bar.open = True
        page.overlay.append(snack_bar)
        page.update()

    def change_view(index: int):
        """Change the current view based on navigation selection."""
        nonlocal current_view
        if index == 0:
            current_view = "admin"
        elif index == 1:
            current_view = "students"
        elif index == 2:
            current_view = "enrol_face"
        elif index == 3:
            current_view = "live_attendance"
        elif index == 4:
            current_view = "fees"
        else:
            current_view = "admin"
        show_main_app()

    def logout(e):
        """Logout current user."""
        nonlocal current_user
        current_user = None
        show_login()

    def show_main_app():
        """Show the main application interface."""
        if page.controls:
            page.controls.clear()

        # Get current window width for responsive layout
        window_width = getattr(page.window, "width", 800)
        is_mobile = window_width < 600

        # Create main layout - Mobile-friendly responsive design
        main_content = None
        if current_view == "students":
            main_content = create_student_view(
                page,
                show_snackbar,
                current_view,
                edit_student_id_container,
                open_attendance_for_student,
                open_fees_for_student,
            )
        elif current_view == "enrol_face":
            main_content = create_enrol_face_view(page, show_snackbar)
        elif current_view == "live_attendance":
            main_content = create_live_attendance_view(page, show_snackbar)
        elif current_view == "admin":
            main_content = create_admin_view(page, show_snackbar)
        elif current_view == "attendance":
            main_content = create_attendance_view(
                page, show_snackbar, selected_student_for_attendance
            )
        elif current_view == "fees":
            main_content = create_fees_view(
                page, show_snackbar, selected_student_for_fees
            )

        if is_mobile:
            # Mobile: Stack navigation at bottom, content above
            page.add(
                create_app_bar(),
                ft.Container(
                    content=main_content,
                    expand=True,
                ),
            )
            # Add navigation rail separately for mobile (will be bottom bar)
            nav_component = create_navigation_rail()
            if nav_component.content:  # Only add if there's content
                page.add(nav_component)
            page.update()
        else:
            # Desktop/Tablet: Side-by-side layout
            page.add(
                create_app_bar(),
                ft.Row(
                    [
                        create_navigation_rail(),
                        ft.VerticalDivider(width=1),
                        ft.Container(
                            content=main_content,
                            expand=True,
                        ),
                    ],
                    expand=True,
                ),
            )
        page.update()

    # Helper functions for navigation
    def open_attendance_for_student(student):
        """Open attendance view for a specific student."""
        nonlocal current_view, selected_student_for_attendance
        current_view = "attendance"
        selected_student_for_attendance = student.id
        show_main_app()

    def open_fees_for_student(student):
        """Open fees view for a specific student."""
        nonlocal current_view, selected_student_for_fees
        current_view = "fees"
        selected_student_for_fees = student.id
        show_main_app()

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

    def open_admin_view():
        """Open admin/database management view."""
        nonlocal current_view
        current_view = "admin"
        show_main_app()


    def create_navigation_rail():
        """Create responsive navigation based on screen size."""
        window_width = getattr(page.window, "width", 800)

        # Get view indices - mapping views to navigation indices
        view_indices = {
            "admin": 0,
            "students": 1,
            "enrol_face": 2,
            "live_attendance": 3,
            "fees": 4,
            "attendance": 1,  # attendance view is part of students
        }
        selected_index = view_indices.get(current_view, 0)

        if window_width < 600:  # Mobile - Use bottom navigation bar
            return ft.Container(
                content=ft.NavigationBar(
                    selected_index=selected_index,
                    destinations=[
                        ft.NavigationBarDestination(
                            icon=ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                            selected_icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                            label="Admin",
                            tooltip="Admin Management",
                        ),
                        ft.NavigationBarDestination(
                            icon=ft.Icons.PEOPLE_OUTLINE,
                            selected_icon=ft.Icons.PEOPLE,
                            label="Students",
                            tooltip="Student Management",
                        ),
                        ft.NavigationBarDestination(
                            icon=ft.Icons.PHOTO_CAMERA_OUTLINED,
                            selected_icon=ft.Icons.PHOTO_CAMERA,
                            label="Enroll Face",
                            tooltip="Face Enrollment",
                        ),
                        ft.NavigationBarDestination(
                            icon=ft.Icons.FACE_UNLOCK_OUTLINED,
                            selected_icon=ft.Icons.FACE_OUTLINED,
                            label="Live Attendance",
                            tooltip="Live Attendance Check",
                        ),
                        ft.NavigationBarDestination(
                            icon=ft.Icons.PAYMENT_OUTLINED,
                            selected_icon=ft.Icons.PAYMENT,
                            label="Fees",
                            tooltip="Fee Management",
                        ),
                    ],
                    on_change=lambda e: change_view(e.control.selected_index),
                    bgcolor=ft.Colors.GREY_100,
                    elevation=8,
                ),
                height=80,
            )

        elif window_width < 1024:  # Tablet - Compact navigation rail
            return ft.Container(
                content=ft.NavigationRail(
                    selected_index=selected_index,
                    label_type=ft.NavigationRailLabelType.SELECTED,
                    min_width=72,
                    destinations=[
                        ft.NavigationRailDestination(
                            icon=ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                            selected_icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                            label="Admin",
                        ),
                        ft.NavigationRailDestination(
                            icon=ft.Icons.PEOPLE_OUTLINE,
                            selected_icon=ft.Icons.PEOPLE,
                            label="Students",
                        ),
                        ft.NavigationRailDestination(
                            icon=ft.Icons.PHOTO_CAMERA_OUTLINED,
                            selected_icon=ft.Icons.PHOTO_CAMERA,
                            label="Enroll Face",
                        ),
                        ft.NavigationRailDestination(
                            icon=ft.Icons.PERSON_SEARCH_OUTLINED,
                            selected_icon=ft.Icons.PERSON_SEARCH,
                            label="Live Attendance",
                        ),
                        ft.NavigationRailDestination(
                            icon=ft.Icons.PAYMENT_OUTLINED,
                            selected_icon=ft.Icons.PAYMENT,
                            label="Fees",
                        ),
                    ],
                    on_change=lambda e: change_view(e.control.selected_index),
                    bgcolor=ft.Colors.GREY_100,
                    elevation=2,
                ),
                width=72,
            )

        else:  # Desktop - Full navigation rail
            return ft.Container(
                content=ft.NavigationRail(
                    selected_index=selected_index,
                    label_type=ft.NavigationRailLabelType.ALL,
                    min_width=100,
                    min_extended_width=200,
                    destinations=[
                        ft.NavigationRailDestination(
                            icon=ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                            selected_icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                            label="Admin",
                        ),
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
                            icon=ft.Icons.PERSON_SEARCH_OUTLINED,
                            selected_icon=ft.Icons.PERSON_SEARCH,
                            label="Live Attendance",
                        ),
                        ft.NavigationRailDestination(
                            icon=ft.Icons.PAYMENT_OUTLINED,
                            selected_icon=ft.Icons.PAYMENT,
                            label="Fees",
                        ),
                    ],
                    on_change=lambda e: change_view(e.control.selected_index),
                    bgcolor=ft.Colors.GREY_100,
                    elevation=2,
                ),
                width=200,
            )

    def show_login():
        """Show login screen."""
        if page.controls:
            page.controls.clear()

        # Use prefix_icon (works in 0.28.3 despite deprecation warning)
        username_field = ft.TextField(
            label="Username",
            prefix_icon=ft.Icons.PERSON,
            width=min(
                300, getattr(page.window, "width", 400) * 0.8
            ),  # Responsive width
            autofocus=True,
        )

        password_field = ft.TextField(
            label="Password",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            width=min(
                300, getattr(page.window, "width", 400) * 0.8
            ),  # Responsive width
        )

        def handle_login(e):
            nonlocal current_user
            username = username_field.value or ""
            password = password_field.value or ""
            if authenticate_user(username, password):
                current_user = username
                show_main_app()
            else:
                show_snackbar("Invalid username or password!", True)

        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Image(
                            src="assets/icon.png",
                            width=min(
                                100, getattr(page.window, "width", 400) * 0.2
                            ),  # Responsive image size
                            height=min(100, getattr(page.window, "width", 400) * 0.2),
                        ),
                        ft.Text(
                            "School Management System",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Divider(height=20),
                        username_field,
                        password_field,
                        ft.ElevatedButton(
                            "Login",
                            icon=ft.Icons.LOGIN,
                            width=min(300, getattr(page.window, "width", 400) * 0.8),
                            on_click=handle_login,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                alignment=ft.alignment.center,
                expand=True,
            )
        )
        page.update()

    # Initialize database and show login
    init_db()
    show_login()


logger = None  # Add this for compatibility with web build if needed

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
