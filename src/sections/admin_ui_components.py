"""
UI Components for Admin Management View.

This module contains reusable UI components for the admin interface,
including day selector and date range picker components with their
associated utility functions.
"""

import flet as ft
import datetime


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


def create_day_selector(page: ft.Page):
    """Create a day selector UI component with checkboxes and quick select buttons."""

    class DaySelector(ft.Container):
        """Day selector container with set_bitmask method."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.page = page
            self.current_bitmask = 0

            # Bitmask values: Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32, Sun=64
            self.days = [
                ("Mon", 1, ft.Icons.LOOKS_ONE),
                ("Tue", 2, ft.Icons.LOOKS_TWO),
                ("Wed", 4, ft.Icons.LOOKS_3),
                ("Thu", 8, ft.Icons.LOOKS_4),
                ("Fri", 16, ft.Icons.LOOKS_5),
                ("Sat", 32, ft.Icons.LOOKS_6),
                ("Sun", 64, ft.Icons.LOOKS)
            ]

            # Create checkboxes
            self.checkboxes = []
            for day_name, bit_value, icon in self.days:
                checkbox = ft.Checkbox(
                    label=day_name,
                    value=False,
                    on_change=lambda e, bv=bit_value: self.update_bitmask(bv, e.control.value)
                )
                self.checkboxes.append(checkbox)

            # Quick select buttons
            self.quick_buttons = ft.Row([
                ft.ElevatedButton(
                    "Weekdays",
                    icon=ft.Icons.WORK,
                    on_click=self.select_weekdays,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_100)
                ),
                ft.ElevatedButton(
                    "Weekends",
                    icon=ft.Icons.WEEKEND,
                    on_click=self.select_weekends,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_100)
                ),
                ft.ElevatedButton(
                    "All Days",
                    icon=ft.Icons.CALENDAR_VIEW_WEEK,
                    on_click=self.select_all_days,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_100)
                ),
            ], spacing=10, alignment=ft.MainAxisAlignment.CENTER)

            # Day checkboxes in a row
            self.checkbox_row = ft.Row(
                [ft.Container(content=cb, width=60) for cb in self.checkboxes],
                spacing=5,
                alignment=ft.MainAxisAlignment.CENTER,
                wrap=True
            )

            # Bitmask display (for debugging/reference)
            self.bitmask_display = ft.Text(
                f"Bitmask: {self.current_bitmask}",
                size=12,
                color=ft.Colors.GREY_600,
                text_align=ft.TextAlign.CENTER
            )

            # Set content
            self.content = ft.Column([
                ft.Text("Select Recurring Days", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("Choose which days this applies to", size=12, color=ft.Colors.GREY_600),
                ft.Divider(),
                self.quick_buttons,
                ft.Container(height=10),
                self.checkbox_row,
                ft.Container(height=10),
                self.bitmask_display,
            ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

            self.padding = 20
            self.border = ft.border.all(1, ft.Colors.OUTLINE)
            self.border_radius = 10
            self.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST

        def update_bitmask(self, bit_value, checked):
            """Update the bitmask when checkbox changes."""
            if checked:
                self.current_bitmask |= bit_value
            else:
                self.current_bitmask &= ~bit_value

            # Update individual checkboxes to reflect current state
            for i, (_, bv, _) in enumerate(self.days):
                self.checkboxes[i].value = (self.current_bitmask & bv) != 0
            self.bitmask_display.value = f"Bitmask: {self.current_bitmask}"
            self.page.update()

        def select_weekdays(self, e):
            """Select Monday through Friday."""
            self.current_bitmask = 31  # Mon-Fri: 1+2+4+8+16 = 31
            self.update_checkboxes()

        def select_weekends(self, e):
            """Select Saturday and Sunday."""
            self.current_bitmask = 96  # Sat-Sun: 32+64 = 96
            self.update_checkboxes()

        def select_all_days(self, e):
            """Select all days of the week."""
            self.current_bitmask = 127  # All days: 1+2+4+8+16+32+64 = 127
            self.update_checkboxes()

        def update_checkboxes(self):
            """Update checkbox states based on current bitmask."""
            for i, (_, bv, _) in enumerate(self.days):
                self.checkboxes[i].value = (self.current_bitmask & bv) != 0
            self.bitmask_display.value = f"Bitmask: {self.current_bitmask}"

        def get_bitmask(self):
            """Get the current bitmask value."""
            return self.current_bitmask

        def set_bitmask(self, bitmask_value):
            """Set the bitmask value and update checkboxes accordingly."""
            self.current_bitmask = bitmask_value & 127  # Ensure valid range (0-127)
            for i, (_, bv, _) in enumerate(self.days):
                self.checkboxes[i].value = (self.current_bitmask & bv) != 0
            self.bitmask_display.value = f"Bitmask: {self.current_bitmask}"
            self.page.update()

    return DaySelector()


def create_date_range_picker(page: ft.Page):
    """Create a date range picker UI component with validation.

    Returns:
        ft.Container: A container with date selection UI components
    """
    # State variables for selected dates
    start_date_value = ""
    end_date_value = ""

    # Date picker dialogs
    start_date_picker = ft.DatePicker(
        on_change=lambda e: on_start_date_change(e.control.value),
        first_date=datetime.date.today(),
        last_date=datetime.date.today() + datetime.timedelta(days=365*2),  # 2 years ahead
    )

    end_date_picker = ft.DatePicker(
        on_change=lambda e: on_end_date_change(e.control.value),
        first_date=datetime.date.today(),
        last_date=datetime.date.today() + datetime.timedelta(days=365*2),  # 2 years ahead
    )

    # Read-only text fields that trigger date pickers
    start_date_field = ft.TextField(
        label="Start Date",
        hint_text="YYYY-MM-DD",
        value="",
        read_only=True,
        prefix_icon=ft.Icons.CALENDAR_TODAY,
        suffix_icon=ft.Icons.ARROW_DROP_DOWN,
        on_click=lambda e: open_start_date_picker(),
        expand=True,
        helper_text="Select start date",
    )

    end_date_field = ft.TextField(
        label="End Date",
        hint_text="YYYY-MM-DD",
        value="",
        read_only=True,
        prefix_icon=ft.Icons.CALENDAR_TODAY,
        suffix_icon=ft.Icons.ARROW_DROP_DOWN,
        on_click=lambda e: open_end_date_picker(),
        expand=True,
        helper_text="Select end date",
    )

    # Error display area
    error_text = ft.Text("", size=12, color=ft.Colors.RED_600, visible=False)

    def on_start_date_change(date_str):
        """Handle start date selection."""
        nonlocal start_date_value
        start_date_value = date_str if date_str else ""
        start_date_field.value = start_date_value

        # Update end date picker minimum date
        if start_date_value:
            try:
                min_end_date = datetime.datetime.strptime(start_date_value, "%Y-%m-%d").date()
                end_date_picker.first_date = min_end_date
            except ValueError:
                pass

        validate_dates()
        update_display()

    def on_end_date_change(date_str):
        """Handle end date selection."""
        nonlocal end_date_value
        end_date_value = date_str if date_str else ""
        end_date_field.value = end_date_value
        validate_dates()
        update_display()

    def open_start_date_picker():
        """Open start date picker dialog."""
        # Add the date picker to page overlay if not already there
        if start_date_picker not in page.overlay:
            page.overlay.append(start_date_picker)
        start_date_picker.open = True
        page.update()

    def open_end_date_picker():
        """Open end date picker dialog."""
        # Add the date picker to page overlay if not already there
        if end_date_picker not in page.overlay:
            page.overlay.append(end_date_picker)
        end_date_picker.open = True
        page.update()

    def validate_dates():
        """Validate that end date is not before start date."""
        nonlocal error_text
        if start_date_value and end_date_value:
            try:
                start_dt = datetime.datetime.strptime(start_date_value, "%Y-%m-%d").date()
                end_dt = datetime.datetime.strptime(end_date_value, "%Y-%m-%d").date()

                if end_dt < start_dt:
                    error_text.value = "End date cannot be before start date"
                    error_text.visible = True
                    end_date_field.border_color = ft.Colors.RED_400
                    start_date_field.border_color = ft.Colors.RED_400
                else:
                    error_text.value = ""
                    error_text.visible = False
                    end_date_field.border_color = None
                    start_date_field.border_color = None
            except ValueError:
                error_text.value = "Invalid date format"
                error_text.visible = True
        else:
            error_text.value = ""
            error_text.visible = False
            end_date_field.border_color = None
            start_date_field.border_color = None

    def update_display():
        """Update the page display."""
        page.update()

    def get_selected_dates():
        """Get the selected date range as a tuple (start_date, end_date)."""
        return (start_date_value, end_date_value) if start_date_value and end_date_value else (None, None)

    def clear_dates():
        """Clear selected dates."""
        nonlocal start_date_value, end_date_value
        start_date_value = ""
        end_date_value = ""
        start_date_field.value = ""
        end_date_field.value = ""
        error_text.value = ""
        error_text.visible = False
        start_date_field.border_color = None
        end_date_field.border_color = None
        update_display()

    def set_dates(start_date, end_date):
        """Set date range programmatically."""
        nonlocal start_date_value, end_date_value
        start_date_value = start_date if start_date else ""
        end_date_value = end_date if end_date else ""
        start_date_field.value = start_date_value
        end_date_field.value = end_date_value
        validate_dates()
        update_display()

    # Create the date range picker UI
    date_picker_container = ft.Container(
        content=ft.Column([
            ft.Text("Date Range Selection", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("Select start and end dates for class management", size=12, color=ft.Colors.GREY_600),
            ft.Divider(),
            ft.Row([
                start_date_field,
                ft.Container(width=20),  # Spacing
                end_date_field,
            ], alignment=ft.MainAxisAlignment.START),
            error_text,
            ft.Container(height=10),
            ft.Row([
                ft.ElevatedButton(
                    "Clear Dates",
                    icon=ft.Icons.CLEAR,
                    on_click=lambda e: clear_dates(),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_100, color=ft.Colors.GREY_800)
                ),
            ], alignment=ft.MainAxisAlignment.END),
        ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.START),
        padding=20,
        border=ft.border.all(1, ft.Colors.OUTLINE),
        border_radius=10,
        bgcolor=getattr(ft.Colors, 'SURFACE_VARIANT', ft.Colors.GREY_50)
    )

    # Create a custom class to hold the methods
    class DateRangePicker(ft.Container):
        def __init__(self, content, **kwargs):
            super().__init__(content=content, **kwargs)
            self.get_selected_dates = get_selected_dates
            self.set_dates = set_dates
            self.clear_dates = clear_dates

    date_picker_container = DateRangePicker(
        content=ft.Column([
            ft.Text("Date Range Selection", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("Select start and end dates for class management", size=12, color=ft.Colors.GREY_600),
            ft.Divider(),
            ft.Row([
                start_date_field,
                ft.Container(width=20),  # Spacing
                end_date_field,
            ], alignment=ft.MainAxisAlignment.START),
            error_text,
            ft.Container(height=10),
            ft.Row([
                ft.ElevatedButton(
                    "Clear Dates",
                    icon=ft.Icons.CLEAR,
                    on_click=lambda e: clear_dates(),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_100, color=ft.Colors.GREY_800)
                ),
            ], alignment=ft.MainAxisAlignment.END),
        ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.START),
        padding=20,
        border=ft.border.all(1, ft.Colors.OUTLINE),
        border_radius=10,
        bgcolor=getattr(ft.Colors, 'SURFACE_VARIANT', ft.Colors.GREY_50)
    )

    return date_picker_container