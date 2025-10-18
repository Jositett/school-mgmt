"""
Admin management view for database CRUD operations.

This view provides interfaces for managing batches, classes, users, and face encodings.
"""

import flet as ft
from database import (
    get_all_batches, add_batch, get_all_classes, add_class,
    get_all_students, get_student_by_id, authenticate_user,
    get_all_fee_templates, add_fee_template, update_fee_template, delete_fee_template,
    get_all_students
)
import sqlite3
import os
import datetime
import datetime

# Import all extracted sections
from sections.admin_utils import (
    get_days_from_bitmask, format_date_range, get_breakpoint,
    responsive_container, ResponsiveRow, ResponsiveCard, MobileListView
)
from sections.admin_ui_components import (
    create_day_selector, create_date_range_picker
)
from sections.admin_stats_section import get_stats_section
from sections.admin_batches_section import create_batches_section
from sections.admin_classes_section import create_classes_section
from sections.admin_fees_section import create_fees_section
from sections.admin_users_section import create_users_section
from sections.admin_face_encodings_section import create_face_encodings_section
from sections.admin_global_search import AdminGlobalSearch, create_global_search_handler


def create_admin_view(page: ft.Page, show_snackbar):
    """Create new admin management view following student view pattern - single scrollable container with organized sections."""

    # Global search state
    global_search_query = ""

    # Global search handler
    def on_global_search_change(e):
        """Handle global search changes."""
        nonlocal global_search_query
        global_search_query = e.control.value or ""
        # Update all sections (they will use the global search as fallback)
        # Each section checks for its own search first, then global
        page.update()

    # Global search field
    global_search_field = ft.TextField(
        label="Search across all sections",
        hint_text="Search batches, classes, users, or face data",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        on_change=on_global_search_change,
    )

    # Build the main view
    return ft.Container(
        content=ft.Column([
            get_stats_section(page),
            ft.Divider(height=1),
            ft.Container(
                content=global_search_field,
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
            ),
            ft.Divider(height=1),
            create_batches_section(page, show_snackbar),
            create_classes_section(page, show_snackbar),
            create_fees_section(page, show_snackbar),
            create_users_section(page, show_snackbar),
            create_face_encodings_section(page, show_snackbar),
        ], spacing=0, expand=True),
        expand=True,
    )