"""
Main entry point for the School Management System.

This file replaces the main function in school_system.py and imports UI views from the views module.
"""

import warnings
# Suppress websockets deprecation warnings since they come from third-party dependencies
warnings.filterwarnings("ignore", message="websockets.legacy is deprecated", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="websockets.server.WebSocketServerProtocol is deprecated", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="remove second argument of ws_handler", category=DeprecationWarning)

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
from navigation import navigation_rail
from utils import export_students_to_csv

# Initialize FaceService singleton
face_service = FaceService()

def main(page: ft.Page):
    """Main application entry point."""
    # ------------------------------------------------------------------
    # Page-level configuration
    # ------------------------------------------------------------------
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.title = "School Management System"
    page.window.width  = 1200
    page.window.height = 800
    page.window.min_width  = 800
    page.window.min_height = 600
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE, use_material3=True)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    current_user = None
    edit_student_id_container = [None]
    current_view = "admin"
    selected_student_for_attendance = None
    selected_student_for_fees      = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def show_snackbar(message: str, is_error: bool = False):
        sb = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.RED_400 if is_error else ft.Colors.GREEN_400,
            open=True,
        )
        page.overlay.append(sb)
        page.update()

    # ---------- view routing ------------------------------------------
    def change_view(index: int):
        nonlocal current_view
        mapping = {0: "admin", 1: "students", 2: "enrol_face",
                   3: "live_attendance", 4: "fees"}
        current_view = mapping.get(index, "admin")
        show_main_app()

    # ---------- logout -------------------------------------------------
    def logout(_):
        nonlocal current_user
        current_user = None
        show_login()

    # ---------- rebuild navigation on resize ---------------------------
    def on_resize(_):
        show_main_app()

    # prefer assigning to the window resize handler; fall back to dynamic setattr if needed
    # use setattr to avoid static type checkers complaining about unknown Window attributes
    try:
        setattr(page.window, "on_resize", on_resize)
    except Exception:
        # If setting on the window fails, attach to the page as a fallback
        setattr(page, "on_resize", on_resize)

    # ---------- open sub-pages from student list -----------------------
    def open_attendance_for_student(student):
        nonlocal current_view, selected_student_for_attendance
        current_view, selected_student_for_attendance = "attendance", student.id
        show_main_app()

    def open_fees_for_student(student):
        nonlocal current_view, selected_student_for_fees
        current_view, selected_student_for_fees = "fees", student.id
        show_main_app()

    # ---------- app-bar ------------------------------------------------
    def create_app_bar():
        return ft.AppBar(
            title=ft.Text("School Management System", weight=ft.FontWeight.BOLD),
            center_title=False,
            bgcolor=ft.Colors.BLUE_700,
            actions=[
                ft.PopupMenuButton(
                    items=[
                        ft.PopupMenuItem(text=f"Logged in as: {current_user}", disabled=True),
                        ft.PopupMenuItem(),
                        ft.PopupMenuItem(text="Logout", icon=ft.Icons.LOGOUT, on_click=logout),
                    ],
                    icon=ft.Icons.ACCOUNT_CIRCLE,
                    icon_color=ft.Colors.WHITE,
                )
            ],
        )



    # ---------- main layout -------------------------------------------
    def show_main_app():
        if page.controls is None:
            page.controls = []
        page.controls.clear()

        w = getattr(page.window, "width", 800)
        is_mobile = w < 600

        # obtain the right content area
        main_content = None
        if current_view == "students":
            main_content = create_student_view(
                page, show_snackbar, current_view, edit_student_id_container,
                open_attendance_for_student, open_fees_for_student)
        elif current_view == "enrol_face":
            main_content = create_enrol_face_view(page, show_snackbar)
        elif current_view == "live_attendance":
            main_content = create_live_attendance_view(page, show_snackbar)
        elif current_view == "admin":
            main_content = create_admin_view(page, show_snackbar)
        elif current_view == "attendance":
            main_content = create_attendance_view(
                page, show_snackbar, selected_student_for_attendance)
        elif current_view == "fees":
            main_content = create_fees_view(
                page, show_snackbar, selected_student_for_fees)

        # ---------------- mobile ---------------------------------------
        if is_mobile:
            nav = navigation_rail(current_view, w, lambda e: change_view(e.control.selected_index))
            page.add(
                create_app_bar(),
                ft.Container(content=main_content, expand=True),
                nav,   # bottom bar wrapped in 80 px Container
            )
        # ---------------- tablet -----------------------------
        elif w < 1024:
            nav = navigation_rail(current_view, w, lambda e: change_view(e.control.selected_index))
            rail_container = ft.Container(
                content=nav,
                width=72,
                height=(page.height or 800) - 56,      # AppBar height
            )

            page.add(
                create_app_bar(),
                ft.Container(
                    content=ft.Row(
                        [
                            rail_container,
                            ft.VerticalDivider(width=1),
                            ft.Container(content=main_content, expand=True),
                        ],
                        expand=True,
                    ),
                    expand=True,
                ),
            )
        # ---------------- desktop -----------------------------
        else:
            nav = navigation_rail(current_view, w, lambda e: change_view(e.control.selected_index))
            page.add(
                create_app_bar(),
                ft.Container(
                    content=ft.Column(
                        [
                            nav,  # horizontal navigation at top
                            ft.Container(content=main_content, expand=True),
                        ],
                        spacing=0,
                    ),
                    expand=True,
                ),
            )
        page.update()

    # ---------- login -------------------------------------------------
    def show_login():
        if page.controls is None:
            page.controls = []
        page.controls.clear()
        user_field = ft.TextField(
            label="Username", prefix_icon=ft.Icons.PERSON,
            width=min(300, getattr(page.window, "width", 400) * 0.8),
            autofocus=True,
        )
        pass_field = ft.TextField(
            label="Password", prefix_icon=ft.Icons.LOCK,
            password=True, can_reveal_password=True,
            width=min(300, getattr(page.window, "width", 400) * 0.8),
        )

        def handle_login(_):
            nonlocal current_user
            if authenticate_user(user_field.value or "", pass_field.value or ""):
                current_user = user_field.value
                show_main_app()
            else:
                show_snackbar("Invalid username or password!", True)

        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Image(
                            src="assets/icon.png",
                            width=min(100, getattr(page.window, "width", 400) * 0.2),
                            height=min(100, getattr(page.window, "width", 400) * 0.2),
                        ),
                        ft.Text("School Management System", size=24, weight=ft.FontWeight.BOLD),
                        ft.Divider(height=20),
                        user_field, pass_field,
                        ft.ElevatedButton(
                            "Login", icon=ft.Icons.LOGIN,
                            width=min(300, getattr(page.window, "width", 400) * 0.8),
                            on_click=handle_login,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                alignment=ft.alignment.center,
                height=page.height,
            )
        )
        page.update()

    # ------------------------------------------------------------------
    # kick-off
    # ------------------------------------------------------------------
    init_db()
    show_login()

logger = None  # Add this for compatibility with web build if needed

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
