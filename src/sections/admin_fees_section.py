"""
Fee templates management section for admin view.
"""

import flet as ft
from database import (
    get_all_batches, add_fee_template, update_fee_template, delete_fee_template,
    get_all_fee_templates, get_all_students
)
import sqlite3


def create_fees_section(page: ft.Page, show_snackbar):
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
        query = search_field.value or ""
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