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


def create_admin_view(page: ft.Page, show_snackbar):
    """Create new admin management view following student view pattern - single scrollable container with organized sections."""

    # Global search state
    global_search_query = ""

    def get_stats_section():
        """Create statistics header section."""
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

            # Define stat cards
            stat_data = [
                {
                    'icon': ft.Icons.PEOPLE,
                    'icon_color': ft.Colors.BLUE_600,
                    'title': 'Students',
                    'value': str(total_students),
                    'value_color': ft.Colors.BLUE_600
                },
                {
                    'icon': ft.Icons.CLASS_,
                    'icon_color': ft.Colors.GREEN_600,
                    'title': 'Classes',
                    'value': str(total_classes),
                    'value_color': ft.Colors.GREEN_600
                },
                {
                    'icon': ft.Icons.SCHOOL,
                    'icon_color': ft.Colors.ORANGE_600,
                    'title': 'Batches',
                    'value': str(total_batches),
                    'value_color': ft.Colors.ORANGE_600
                },
                {
                    'icon': ft.Icons.FACE,
                    'icon_color': ft.Colors.PURPLE_600,
                    'title': 'Face Data',
                    'value': str(total_encodings),
                    'value_color': ft.Colors.PURPLE_600
                }
            ]

            cards = []
            for data in stat_data:
                card_content = ft.Column([
                    ft.Icon(data['icon'], size=32, color=data['icon_color']),
                    ft.Text(data['title'], size=12, weight=ft.FontWeight.BOLD),
                    ft.Text(data['value'], size=24, weight=ft.FontWeight.BOLD, color=data['value_color']),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=5)

                card = ResponsiveCard(card_content)
                cards.append(ft.Container(content=card, expand=True))

            # Responsive layout
            breakpoint = get_breakpoint(page)
            if breakpoint == 'mobile':
                layout = ft.Column(cards, spacing=10)
            else:
                layout = ResponsiveRow(cards, alignment=ft.MainAxisAlignment.CENTER, spacing=15)

            return ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text("Admin Management", size=28, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER),
                    layout
                ], spacing=15),
                padding=20,
            )
        except Exception as ex:
            return ft.Container(content=ft.Text(f"Error loading stats: {ex}", color=ft.Colors.RED_600))

    def create_batches_section():
        """Create batches management section following student view pattern."""

        # State variables
        edit_batch_id = None

        # Form fields
        batch_name_field = ft.TextField(
            label="Batch Name",
            hint_text="e.g., 2024-2025",
            prefix_icon=ft.Icons.SCHOOL,
            expand=True,
        )

        start_time_field = ft.TextField(
            label="Start Time",
            hint_text="HH:MM",
            prefix_icon=ft.Icons.SCHEDULE,
            value="09:00",
            width=120,
        )

        end_time_field = ft.TextField(
            label="End Time",
            hint_text="HH:MM",
            prefix_icon=ft.Icons.SCHEDULE,
            value="17:00",
            width=120,
        )

        def save_batch(e):
            """Save or update batch."""
            if not batch_name_field.value or not start_time_field.value or not end_time_field.value:
                show_snackbar("All fields are required!", True)
                return

            if edit_batch_id is None:
                if add_batch(batch_name_field.value, start_time_field.value, end_time_field.value):
                    show_snackbar("Batch added successfully!")
                    clear_batch_form()
                    update_batch_list()
                else:
                    show_snackbar("Error adding batch! Name may already exist.", True)
            else:
                # Check for duplicate name first
                try:
                    conn = sqlite3.connect("school.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM batches WHERE name = ? AND id != ?", (batch_name_field.value, edit_batch_id))
                    if cursor.fetchone():
                        show_snackbar("Batch name already exists!", True)
                        conn.close()
                        return
                    cursor.execute("""
                        UPDATE batches SET name = ?, start_time = ?, end_time = ?
                        WHERE id = ?
                    """, (batch_name_field.value, start_time_field.value, end_time_field.value, edit_batch_id))
                    if cursor.rowcount > 0:
                        conn.commit()
                        show_snackbar("Batch updated successfully!")
                        clear_batch_form()
                        update_batch_list()
                    else:
                        show_snackbar("Error updating batch: Batch not found!", True)
                    conn.close()
                except Exception as ex:
                    show_snackbar(f"Error updating batch: {ex}", True)

        # Save button (defined after function so it can access save_batch)
        save_button = ft.ElevatedButton(
            "Save Batch",
            icon=ft.Icons.SAVE,
            on_click=save_batch,
        )

        # Section-specific search
        search_field = ft.TextField(
            label="Search batches",
            hint_text="Search by name or time",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=lambda e: update_batch_list(),
        )

        batch_list_view = ft.ListView(spacing=10, padding=20, expand=True)

        def update_batch_list():
            """Update the batch list display."""
            query = search_field.value or global_search_query
            batches = get_all_batches()

            if query:
                batches = [b for b in batches if query.lower() in b.name.lower() or query in str(b.start_time) or query in str(b.end_time)]

            batch_list_view.controls.clear()

            if not batches:
                batch_list_view.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.GREY_400),
                            ft.Text("No batches found", size=16, color=ft.Colors.GREY_600),
                            ft.Text("Add your first batch below", size=12, color=ft.Colors.GREY_500),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=40,
                    )
                )
            else:
                for batch in batches:
                    # Count students in this batch
                    students_count = len([s for s in get_all_students() if s.batch_id == batch.id])

                    batch_list_view.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.CircleAvatar(
                                            content=ft.Text(batch.name[0].upper(), size=20, weight=ft.FontWeight.BOLD),
                                            bgcolor=ft.Colors.ORANGE_200,
                                            color=ft.Colors.ORANGE_900,
                                        ),
                                        width=50,
                                    ),
                                    ft.Column([
                                        ft.Text(batch.name, weight=ft.FontWeight.BOLD, size=16),
                                        ft.Row([
                                            ft.Icon(ft.Icons.PEOPLE, size=14, color=ft.Colors.GREY_600),
                                            ft.Text(f"{students_count} students", size=12, color=ft.Colors.GREY_600),
                                            ft.VerticalDivider(width=1),
                                            ft.Icon(ft.Icons.SCHEDULE, size=14, color=ft.Colors.GREY_600),
                                            ft.Text(f"{batch.start_time} - {batch.end_time}", size=12, color=ft.Colors.GREY_600),
                                        ], spacing=5),
                                    ], spacing=5, expand=True),
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT,
                                            icon_color=ft.Colors.BLUE_700,
                                            tooltip="Edit",
                                            on_click=lambda e, b=batch: edit_batch(b),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            icon_color=ft.Colors.RED_700,
                                            tooltip="Delete",
                                            on_click=lambda e, b=batch: confirm_delete_batch(b),
                                        ),
                                    ], spacing=0),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                padding=15,
                            ),
                        )
                    )
            page.update()

        def edit_batch(batch):
            """Load batch data for editing."""
            nonlocal edit_batch_id
            edit_batch_id = batch.id
            batch_name_field.value = batch.name
            start_time_field.value = batch.start_time
            end_time_field.value = batch.end_time
            save_button.text = "Update Batch"
            save_button.icon = ft.Icons.UPDATE
            page.update()

        def clear_batch_form():
            """Clear batch form fields."""
            nonlocal edit_batch_id
            edit_batch_id = None
            batch_name_field.value = ""
            start_time_field.value = "09:00"
            end_time_field.value = "17:00"
            save_button.text = "Save Batch"
            save_button.icon = ft.Icons.SAVE
            page.update()

        def confirm_delete_batch(batch):
            """Show confirmation dialog for deleting batch."""
            def delete_confirmed(e):
                try:
                    # Check if batch is in use
                    students_using = len([s for s in get_all_students() if s.batch_id == batch.id])
                    if students_using > 0:
                        show_snackbar(f"Cannot delete: {students_using} students are in this batch!", True)
                        return

                    conn = sqlite3.connect("school.db")
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM batches WHERE id = ?", (batch.id,))
                    conn.commit()
                    conn.close()
                    show_snackbar("Batch deleted successfully!")
                    update_batch_list()
                except Exception as ex:
                    show_snackbar(f"Error deleting batch: {ex}", True)
                dialog.open = False
                page.update()

            def cancel_delete(e):
                dialog.open = False
                page.update()

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirm Delete"),
                content=ft.Text(f"Are you sure you want to delete batch '{batch.name}'?\nThis action cannot be undone."),
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

        def add_batch_quick(e):
            """Quick add batch dialog."""
            name_field = ft.TextField(label="Batch Name", hint_text="e.g., 2025-2026", autofocus=True)
            start_field = ft.TextField(label="Start Time", value="09:00", width=100)
            end_field = ft.TextField(label="End Time", value="17:00", width=100)

            def save_quick(e):
                if name_field.value and start_field.value and end_field.value:
                    if add_batch(name_field.value, start_field.value, end_field.value):
                        update_batch_list()
                        show_snackbar("Batch added successfully!")
                        dlg.open = False
                        page.update()
                    else:
                        show_snackbar("Error adding batch! Name may already exist.", True)
                else:
                    show_snackbar("All fields are required!", True)

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Add New Batch"),
                content=ft.Container(
                    content=ft.Column([
                        name_field,
                        ft.Row([start_field, end_field], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                    ], spacing=15, tight=True),
                    width=300,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: (setattr(dlg, 'open', False), page.update())),
                    ft.ElevatedButton("Add Batch", on_click=save_quick),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        # Initialize
        update_batch_list()

        # Build section
        return ft.Container(
            content=ft.Column([
                ft.Text("Batch Management", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_700),
                ft.Text("Manage class batches and schedules", size=12, color=ft.Colors.GREY_600),
                ft.Divider(),
                search_field,
                ft.Container(
                    content=ft.Column([
                        ft.Text("Add / Edit Batch", size=14, weight=ft.FontWeight.W_500),
                        ft.Row([
                            batch_name_field,
                            start_time_field,
                            end_time_field,
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE,
                                icon_color=ft.Colors.ORANGE_700,
                                tooltip="Quick Add Batch",
                                on_click=add_batch_quick,
                            ),
                        ]),
                        ft.Row([
                            save_button,
                            ft.OutlinedButton(
                                "Clear",
                                icon=ft.Icons.CLEAR,
                                on_click=lambda e: clear_batch_form(),
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
                        ft.Text("Batches List", size=14, weight=ft.FontWeight.W_500),
                        ft.Container(content=batch_list_view, expand=True),
                    ], spacing=10),
                    expand=True,
                ),
            ], spacing=15),
            padding=20,
        )

    def create_classes_section():
        """Create classes management section."""

        # State variables
        edit_class_id = None

        # Form fields
        class_name_field = ft.TextField(
            label="Class Name",
            hint_text="e.g., Grade 10A",
            prefix_icon=ft.Icons.CLASS_,
            expand=True,
        )

        start_time_field = ft.TextField(
            label="Start Time",
            hint_text="HH:MM",
            prefix_icon=ft.Icons.SCHEDULE,
            value="09:00",
            width=120,
        )

        end_time_field = ft.TextField(
            label="End Time",
            hint_text="HH:MM",
            prefix_icon=ft.Icons.SCHEDULE,
            value="15:00",
            width=120,
        )

        # Section-specific search
        search_field = ft.TextField(
            label="Search classes",
            hint_text="Search by name",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=lambda e: update_class_list(),
        )

        class_list_view = ft.ListView(spacing=10, padding=20, expand=True)

        def update_class_list():
            """Update the class list display."""
            query = search_field.value or global_search_query
            classes = get_all_classes()

            if query:
                classes = [c for c in classes if query.lower() in c.name.lower()]

            class_list_view.controls.clear()

            if not classes:
                class_list_view.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.GREY_400),
                            ft.Text("No classes found", size=16, color=ft.Colors.GREY_600),
                            ft.Text("Add your first class below", size=12, color=ft.Colors.GREY_500),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=40,
                    )
                )
            else:
                for cls in classes:
                    # Count students in this class
                    students_count = len([s for s in get_all_students() if s.class_id == cls.id])

                    # Prepare scheduling info row
                    scheduling_info = []
                    days_text = get_days_from_bitmask(cls.recurrence_pattern)
                    date_range_text = format_date_range(cls.start_date, cls.end_date)

                    if days_text and days_text != "Daily":
                        scheduling_info.extend([
                            ft.Icon(ft.Icons.CALENDAR_VIEW_WEEK, size=14, color=ft.Colors.BLUE_600),
                            ft.Text(days_text, size=12, color=ft.Colors.BLUE_600),
                        ])

                    if date_range_text:
                        if scheduling_info:
                            scheduling_info.append(ft.VerticalDivider(width=1))
                        scheduling_info.extend([
                            ft.Icon(ft.Icons.DATE_RANGE, size=14, color=ft.Colors.BLUE_600),
                            ft.Text(date_range_text, size=12, color=ft.Colors.BLUE_600),
                        ])

                    class_list_view.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.CircleAvatar(
                                            content=ft.Text(cls.name[0].upper(), size=20, weight=ft.FontWeight.BOLD),
                                            bgcolor=ft.Colors.GREEN_200,
                                            color=ft.Colors.GREEN_900,
                                        ),
                                        width=50,
                                    ),
                                    ft.Column([
                                        ft.Text(cls.name, weight=ft.FontWeight.BOLD, size=16),
                                        ft.Row([
                                            ft.Icon(ft.Icons.PEOPLE, size=14, color=ft.Colors.GREY_600),
                                            ft.Text(f"{students_count} students", size=12, color=ft.Colors.GREY_600),
                                            ft.VerticalDivider(width=1),
                                            ft.Icon(ft.Icons.SCHEDULE, size=14, color=ft.Colors.GREY_600),
                                            ft.Text(f"{cls.start_time} - {cls.end_time}", size=12, color=ft.Colors.GREY_600),
                                        ], spacing=5),
                                        ft.Row(scheduling_info, spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER) if scheduling_info else ft.Container(),
                                    ], spacing=5, expand=True),
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT,
                                            icon_color=ft.Colors.BLUE_700,
                                            tooltip="Edit",
                                            on_click=lambda e, c=cls: edit_class(c),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            icon_color=ft.Colors.RED_700,
                                            tooltip="Delete",
                                            on_click=lambda e, c=cls: confirm_delete_class(c),
                                        ),
                                    ], spacing=0),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                padding=15,
                            ),
                        )
                    )
            page.update()

        def edit_class(cls):
            """Load class data for editing."""
            nonlocal edit_class_id
            edit_class_id = cls.id
            class_name_field.value = cls.name
            start_time_field.value = cls.start_time
            end_time_field.value = cls.end_time
            page.update()

        def clear_class_form():
            """Clear class form fields."""
            nonlocal edit_class_id
            edit_class_id = None
            class_name_field.value = ""
            start_time_field.value = "09:00"
            end_time_field.value = "15:00"
            page.update()

        def save_class(e):
            """Save or update class."""
            if not class_name_field.value or not start_time_field.value or not end_time_field.value:
                show_snackbar("All fields are required!", True)
                return

            if edit_class_id is None:
                if add_class(class_name_field.value, start_time_field.value, end_time_field.value):
                    show_snackbar("Class added successfully!")
                    clear_class_form()
                    update_class_list()
                else:
                    show_snackbar("Error adding class! Name may already exist.", True)
            else:
                # Check for duplicate name first
                try:
                    conn = sqlite3.connect("school.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM classes WHERE name = ? AND id != ?", (class_name_field.value, edit_class_id))
                    if cursor.fetchone():
                        show_snackbar("Class name already exists!", True)
                        conn.close()
                        return
                    cursor.execute("""
                        UPDATE classes SET name = ?, start_time = ?, end_time = ?
                        WHERE id = ?
                    """, (class_name_field.value, start_time_field.value, end_time_field.value, edit_class_id))
                    if cursor.rowcount > 0:
                        conn.commit()
                        show_snackbar("Class updated successfully!")
                        clear_class_form()
                        update_class_list()
                    else:
                        show_snackbar("Error updating class: Class not found!", True)
                    conn.close()
                except Exception as ex:
                    show_snackbar(f"Error updating class: {ex}", True)

        def confirm_delete_class(cls):
            """Show confirmation dialog for deleting class."""
            def delete_confirmed(e):
                try:
                    # Check if class is in use
                    students_using = len([s for s in get_all_students() if s.class_id == cls.id])
                    if students_using > 0:
                        show_snackbar(f"Cannot delete: {students_using} students are in this class!", True)
                        return

                    conn = sqlite3.connect("school.db")
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM classes WHERE id = ?", (cls.id,))
                    conn.commit()
                    conn.close()
                    show_snackbar("Class deleted successfully!")
                    update_class_list()
                except Exception as ex:
                    show_snackbar(f"Error deleting class: {ex}", True)
                dialog.open = False
                page.update()

            def cancel_delete(e):
                dialog.open = False
                page.update()

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirm Delete"),
                content=ft.Text(f"Are you sure you want to delete class '{cls.name}'?\nThis action cannot be undone."),
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

        def add_class_quick(e):
            """Quick add class dialog."""
            name_field = ft.TextField(label="Class Name", hint_text="e.g., Grade 10A", autofocus=True)
            start_field = ft.TextField(label="Start Time", value="09:00", width=100)
            end_field = ft.TextField(label="End Time", value="15:00", width=100)

            def save_quick(e):
                if name_field.value and start_field.value and end_field.value:
                    if add_class(name_field.value, start_field.value, end_field.value):
                        update_class_list()
                        show_snackbar("Class added successfully!")
                        dlg.open = False
                        page.update()
                    else:
                        show_snackbar("Error adding class! Name may already exist.", True)
                else:
                    show_snackbar("All fields are required!", True)

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Add New Class"),
                content=ft.Container(
                    content=ft.Column([
                        name_field,
                        ft.Row([start_field, end_field], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                    ], spacing=15, tight=True),
                    width=350,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: (setattr(dlg, 'open', False), page.update())),
                    ft.ElevatedButton("Add Class", on_click=save_quick),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        # Initialize
        update_class_list()

        # Build section
        return ft.Container(
            content=ft.Column([
                ft.Text("Class Management", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700),
                ft.Text("Manage student classes", size=12, color=ft.Colors.GREY_600),
                ft.Divider(),
                search_field,
                ft.Container(
                    content=ft.Column([
                        ft.Text("Add / Edit Class", size=14, weight=ft.FontWeight.W_500),
                        ft.Row([
                            class_name_field,
                            start_time_field,
                            end_time_field,
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE,
                                icon_color=ft.Colors.GREEN_700,
                                tooltip="Quick Add Class",
                                on_click=add_class_quick,
                            ),
                        ]),
                        ft.Row([
                            ft.ElevatedButton(
                                "Save Class" if edit_class_id is None else "Update Class",
                                icon=ft.Icons.SAVE,
                                on_click=save_class,
                            ),
                            ft.OutlinedButton(
                                "Clear",
                                icon=ft.Icons.CLEAR,
                                on_click=lambda e: clear_class_form(),
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
                        ft.Text("Classes List", size=14, weight=ft.FontWeight.W_500),
                        ft.Container(content=class_list_view, expand=True),
                    ], spacing=10),
                    expand=True,
                ),
            ], spacing=15),
            padding=20,
        )

    def create_users_section():
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

    def create_face_encodings_section():
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
            query = search_field.value or global_search_query

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

    def create_fees_section():
        """Create fee templates management section."""

        # State variables
        edit_template_id = None

        # Form fields
        template_name_field = ft.TextField(
            label="Template Name",
            hint_text="e.g., Registration Fee, Monthly Tuition",
            prefix_icon=ft.Icons.DESCRIPTION,
            expand=True,
        )

        description_field = ft.TextField(
            label="Description",
            hint_text="Optional description of the fee",
            prefix_icon=ft.Icons.INFO,
            expand=True,
        )

        amount_field = ft.TextField(
            label="Amount",
            hint_text="e.g., 500.00",
            prefix_icon=ft.Icons.MONEY,
            width=150,
        )

        frequency_dropdown = ft.Dropdown(
            label="Frequency",
            hint_text="Select fee frequency",
            options=[
                ft.dropdown.Option("One-time", "One-time"),
                ft.dropdown.Option("Monthly", "Monthly"),
                ft.dropdown.Option("Annual", "Annual"),
            ],
            value="One-time",
            width=150,
        )

        batch_dropdown = ft.Dropdown(
            label="Apply to Batch (Optional)",
            hint_text="Leave empty for all batches",
            options=[
                ft.dropdown.Option(str(batch.id), batch.name) for batch in get_all_batches()
            ],
            width=200,
        )

        # Section-specific search
        search_field = ft.TextField(
            label="Search fee templates",
            hint_text="Search by name or description",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=lambda e: update_fee_template_list(),
        )

        template_list_view = ft.ListView(spacing=10, padding=20, expand=True)

        def save_fee_template(e):
            """Save or update fee template."""
            if not template_name_field.value or not amount_field.value:
                show_snackbar("Template name and amount are required!", True)
                return

            try:
                amount = float(amount_field.value or "0")
                batch_id = int(batch_dropdown.value) if batch_dropdown.value else None
            except ValueError:
                show_snackbar("Invalid amount format!", True)
                return

            if edit_template_id is None:
                if add_fee_template(
                    template_name_field.value,
                    description_field.value or "",
                    amount,
                    frequency_dropdown.value or "One-time",
                    batch_id
                ):
                    show_snackbar("Fee template added successfully!")
                    clear_fee_template_form()
                    update_fee_template_list()
                else:
                    show_snackbar("Error adding fee template! Name may already exist.", True)
            else:
                if update_fee_template(
                    edit_template_id,
                    template_name_field.value,
                    description_field.value or "",
                    amount,
                    frequency_dropdown.value or "One-time",
                    batch_id
                ):
                    show_snackbar("Fee template updated successfully!")
                    clear_fee_template_form()
                    update_fee_template_list()
                else:
                    show_snackbar("Error updating fee template!", True)

        def update_fee_template_list():
            """Update the fee template list display."""
            query = search_field.value or global_search_query
            templates = get_all_fee_templates()

            if query:
                templates = [t for t in templates
                           if query.lower() in t.name.lower()
                           or query.lower() in t.description.lower()
                           or query.lower() in t.batch_name.lower()]

            template_list_view.controls.clear()

            if not templates:
                template_list_view.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.GREY_400),
                            ft.Text("No fee templates found", size=16, color=ft.Colors.GREY_600),
                            ft.Text("Add your first fee template below", size=12, color=ft.Colors.GREY_500),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=40,
                    )
                )
            else:
                for template in templates:
                    # Count applications
                    try:
                        conn = sqlite3.connect("school.db")
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT COUNT(*) FROM fee_applications
                            WHERE template_id = ?
                        """, (template.id,))
                        applications_count = cursor.fetchone()[0]
                        conn.close()
                    except:
                        applications_count = 0

                    template_list_view.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.CircleAvatar(
                                            content=ft.Text(template.name[0].upper(), size=20, weight=ft.FontWeight.BOLD),
                                            bgcolor=ft.Colors.BLUE_200 if template.is_active else ft.Colors.GREY_300,
                                            color=ft.Colors.BLUE_900 if template.is_active else ft.Colors.GREY_700,
                                        ),
                                        width=50,
                                    ),
                                    ft.Column([
                                        ft.Row([
                                            ft.Text(template.name, weight=ft.FontWeight.BOLD, size=16),
                                            ft.Chip(
                                                label=ft.Text(template.frequency, size=10),
                                                bgcolor={
                                                    'One-time': ft.Colors.GREEN_100,
                                                    'Monthly': ft.Colors.BLUE_100,
                                                    'Annual': ft.Colors.ORANGE_100
                                                }.get(template.frequency, ft.Colors.GREY_100),
                                                color={
                                                    'One-time': ft.Colors.GREEN_800,
                                                    'Monthly': ft.Colors.BLUE_800,
                                                    'Annual': ft.Colors.ORANGE_800
                                                }.get(template.frequency, ft.Colors.GREY_800),
                                            ),
                                        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                        ft.Text(template.description or "No description",
                                               size=12, color=ft.Colors.GREY_600, max_lines=1),
                                        ft.Row([
                                            ft.Text(f"{template.amount:.2f}", size=12, color=ft.Colors.GREEN_600),
                                            ft.VerticalDivider(width=1),
                                            ft.Icon(ft.Icons.GROUPS, size=14, color=ft.Colors.GREY_600),
                                            ft.Text(f"{applications_count} applied", size=12, color=ft.Colors.GREY_600),
                                            ft.VerticalDivider(width=1),
                                            ft.Text(template.batch_name, size=12, color=ft.Colors.GREY_600),
                                        ], spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                    ], spacing=5, expand=True),
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT,
                                            icon_color=ft.Colors.BLUE_700,
                                            tooltip="Edit",
                                            on_click=lambda e, t=template: edit_fee_template(t),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            icon_color=ft.Colors.RED_700,
                                            tooltip="Delete",
                                            on_click=lambda e, t=template: confirm_delete_fee_template(t),
                                        ),
                                        ft.Switch(
                                            value=template.is_active,
                                            on_change=lambda e, t=template: toggle_template_active(t, e.control.value),
                                            scale=0.8,
                                        ),
                                    ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                padding=15,
                            ),
                        )
                    )
            page.update()

        def edit_fee_template(template):
            """Load template data for editing."""
            nonlocal edit_template_id
            edit_template_id = template.id
            template_name_field.value = template.name
            description_field.value = template.description
            amount_field.value = str(template.amount)
            frequency_dropdown.value = template.frequency
            batch_dropdown.value = str(template.batch_id) if template.batch_id else None
            page.update()

        def clear_fee_template_form():
            """Clear fee template form fields."""
            nonlocal edit_template_id
            edit_template_id = None
            template_name_field.value = ""
            description_field.value = ""
            amount_field.value = ""
            frequency_dropdown.value = "One-time"
            batch_dropdown.value = None
            page.update()

        def toggle_template_active(template, is_active):
            """Toggle fee template active status."""
            if update_fee_template(template.id, template.name, template.description,
                                 template.amount, template.frequency, template.batch_id, is_active):
                show_snackbar(f"Template {'activated' if is_active else 'deactivated'}!")
                update_fee_template_list()
            else:
                show_snackbar("Error updating template status!", True)

        def confirm_delete_fee_template(template):
            """Show confirmation dialog for deleting fee template."""
            def delete_confirmed(e):
                if delete_fee_template(template.id):
                    show_snackbar("Fee template deleted successfully!")
                    update_fee_template_list()
                else:
                    show_snackbar("Error deleting fee template!", True)
                dialog.open = False
                page.update()

            def cancel_delete(e):
                dialog.open = False
                page.update()

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirm Delete"),
                content=ft.Text(f"Are you sure you want to delete fee template '{template.name}'?\nThis will also delete all associated fee records."),
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

        def add_fee_template_quick(e):
            """Quick add fee template dialog."""
            name_field = ft.TextField(label="Template Name", hint_text="e.g., Registration Fee", autofocus=True)
            amount_field_quick = ft.TextField(label="Amount", hint_text="500.00", width=120)
            freq_dd = ft.Dropdown(
                label="Frequency",
                options=[
                    ft.dropdown.Option("One-time", "One-time"),
                    ft.dropdown.Option("Monthly", "Monthly"),
                    ft.dropdown.Option("Annual", "Annual"),
                ],
                value="One-time",
                width=120,
            )

            def save_quick(e):
                try:
                    amount = float(amount_field_quick.value or "0")
                    if name_field.value and add_fee_template(
                        name_field.value,
                        "",
                        amount,
                        freq_dd.value or "One-time",
                        None
                    ):
                        update_fee_template_list()
                        show_snackbar("Fee template added successfully!")
                        dlg.open = False
                        page.update()
                    else:
                        show_snackbar("Error adding fee template!", True)
                except ValueError:
                    show_snackbar("Invalid amount format!", True)

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Add New Fee Template"),
                content=ft.Container(
                    content=ft.Column([
                        name_field,
                        ft.Row([amount_field_quick, freq_dd], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                    ], spacing=15, tight=True),
                    width=350,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: (setattr(dlg, 'open', False), page.update())),
                    ft.ElevatedButton("Add Template", on_click=save_quick),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        # Initialize
        update_fee_template_list()

        # Build section
        return ft.Container(
            content=ft.Column([
                ft.Text("Fee Templates", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_700),
                ft.Text("Create and manage fee templates for automated fee generation", size=12, color=ft.Colors.GREY_600),
                ft.Divider(),
                search_field,
                ft.Container(
                    content=ft.Column([
                        ft.Text("Add / Edit Fee Template", size=14, weight=ft.FontWeight.W_500),
                        ft.Row([
                            template_name_field,
                            amount_field,
                            frequency_dropdown,
                            batch_dropdown,
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE,
                                icon_color=ft.Colors.INDIGO_700,
                                tooltip="Quick Add Template",
                                on_click=add_fee_template_quick,
                            ),
                        ]),
                        ft.Row([
                            description_field,
                        ]),
                        ft.Row([
                            ft.ElevatedButton(
                                "Save Template" if edit_template_id is None else "Update Template",
                                icon=ft.Icons.SAVE,
                                on_click=save_fee_template,
                            ),
                            ft.OutlinedButton(
                                "Clear",
                                icon=ft.Icons.CLEAR,
                                on_click=lambda e: clear_fee_template_form(),
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
                        ft.Text("Fee Templates List", size=14, weight=ft.FontWeight.W_500),
                        ft.Container(content=template_list_view, expand=True),
                    ], spacing=10),
                    expand=True,
                ),
            ], spacing=15),
            padding=20,
        )

    # Build the main view
    return ft.Container(
        content=ft.Column([
            get_stats_section(),
            ft.Divider(height=1),
            ft.Container(
                content=global_search_field,
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
            ),
            ft.Divider(height=1),
            create_batches_section(),
            create_classes_section(),
            create_fees_section(),
            create_users_section(),
            create_face_encodings_section(),
        ], spacing=0, expand=True),
        expand=True,
    )
