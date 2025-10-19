"""
Navigation utilities for the School Management System.

Provides responsive navigation that adapts based on screen width:
- NavigationBar for mobile (< 600px)
- Collapsible NavigationRail for tablet (600-1024px)
- Horizontal NavigationBar for desktop (>= 1024px)
"""

import flet as ft


def navigation_rail(current_view: str, page_width: float, on_change):
    """Return the correct navigation widget for the current form-factor."""
    view_to_idx = {"admin": 0, "students": 1, "attendance": 1,
                   "enrol_face": 2, "live_attendance": 3, "fees": 4}
    idx = view_to_idx.get(current_view, 0)

    # Define navigation descriptors once (icon, selected_icon, label, tooltip)
    dest_defs = [
        (ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, ft.Icons.ADMIN_PANEL_SETTINGS, "Admin", "Admin Management"),
        (ft.Icons.PEOPLE_OUTLINE, ft.Icons.PEOPLE, "Students", "Student Management"),
        (ft.Icons.PHOTO_CAMERA_OUTLINED, ft.Icons.PHOTO_CAMERA, "Enrol Face", "Face Enrollment"),
        (ft.Icons.FACE_UNLOCK_OUTLINED, ft.Icons.FACE_OUTLINED, "Live Attendance", "Live Attendance Check"),
        (ft.Icons.PAYMENT_OUTLINED, ft.Icons.PAYMENT, "Fees", "Fee Management"),
    ]

    # Build type-correct destination lists for each widget
    destinations_bar = [
        ft.NavigationBarDestination(
            icon=icon,
            selected_icon=selected_icon,
            label=label
        ) for icon, selected_icon, label, tooltip in dest_defs
    ]

    destinations_rail = [
        ft.NavigationRailDestination(
            icon=icon,
            selected_icon=selected_icon,
            label=label
        ) for icon, selected_icon, label, tooltip in dest_defs
    ]
    if page_width < 600:                       # phone
        return ft.Container(
            content=ft.NavigationBar(
                destinations=destinations_bar,
                selected_index=idx,
                on_change=on_change,
                elevation=8,
            ),
            height=80,
        )

    elif page_width < 1024:  # tablet
        return ft.NavigationRail(
            destinations=destinations_rail,
            selected_index=idx,
            label_type=ft.NavigationRailLabelType.SELECTED,
            min_width=72, expand=True,
            on_change=on_change,
            elevation=2,
        )

    # desktop (>= 1024px) - horizontal navigation at top
    else:
        return ft.Container(
            content=ft.NavigationBar(
                destinations=destinations_bar,
                selected_index=idx,
                on_change=on_change,
                elevation=2,
            ),
            height=72,  # standard height for navigation bar
        )
