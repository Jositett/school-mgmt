"""
Utility functions and components for admin views.

This module contains reusable utility functions and responsive UI components
extracted from admin_view.py for better organization and reusability.
"""

import flet as ft


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


# Responsive Design Utilities
def get_breakpoint(page):
    """Get current responsive breakpoint based on window width with improved detection."""
    try:
        # Get width from page.window or fallback to page width
        width = getattr(page.window, 'width', getattr(page, 'width', 800))
        if width < 768:
            return 'mobile'
        elif width < 1024:
            return 'tablet'
        else:
            return 'desktop'
    except AttributeError:
        # Fallback for cases where window attributes aren't available
        return 'desktop'


def responsive_container(content, mobile_props=None, tablet_props=None, desktop_props=None):
    """Create a responsive container with breakpoint-specific properties."""
    def update_container(e):
        breakpoint = get_breakpoint(e.page)
        props = {
            'mobile': mobile_props or {},
            'tablet': tablet_props or {},
            'desktop': desktop_props or {}
        }.get(breakpoint, {})

        for key, value in props.items():
            setattr(container, key, value)
        e.page.update()

    container = ft.Container(content=content)

    # Set initial properties - use default values since we can't create a Page instance
    props = {'mobile': mobile_props or {}, 'tablet': tablet_props or {}, 'desktop': desktop_props or {}}
    initial_props = props.get('desktop', {})  # Default to desktop

    for key, value in initial_props.items():
        setattr(container, key, value)

    return container


def ResponsiveRow(controls, **kwargs):
    """Responsive Row component that adapts to screen size."""
    def get_layout_props(breakpoint):
        if breakpoint == 'mobile':
            return {'alignment': ft.MainAxisAlignment.CENTER, 'spacing': 10}
        elif breakpoint == 'tablet':
            return {'alignment': ft.MainAxisAlignment.START, 'spacing': 15}
        else:  # desktop
            return {'alignment': ft.MainAxisAlignment.START, 'spacing': 20}

    layout_props = get_layout_props('desktop')  # Default
    layout_props.update(kwargs)

    return ft.Row(controls, **layout_props)


def ResponsiveCard(content, **kwargs):
    """Responsive Card component."""
    return ft.Card(
        content=ft.Container(content=content, padding=15),
        elevation=2,
        **kwargs
    )


def MobileListView(items, breakpoint):
    """Convert table data to mobile-friendly card list."""
    if breakpoint != 'mobile':
        return None

    cards = []
    for item in items:
        card_content = ft.Column([
            ft.Text(item.get('title', ''), size=16, weight=ft.FontWeight.BOLD),
            ft.Text(item.get('subtitle', ''), size=12, color=ft.Colors.GREY_600),
        ], spacing=5)

        if 'actions' in item:
            card_content.controls.append(
                ft.Row(item['actions'], alignment=ft.MainAxisAlignment.END)
            )

        cards.append(
            ft.Container(
                content=ResponsiveCard(card_content),
                margin=ft.margin.only(bottom=8)
            )
        )

    return ft.Column(cards)