"""
Batch management section for admin view.

This module provides the batches management interface with CRUD operations.
"""

import flet as ft
import sqlite3
import os
from database import get_all_batches, add_batch, get_all_students


def create_batches_section(page: ft.Page, show_snackbar):
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

    def save_batch(e):
        """Save or update batch."""
        if not batch_name_field.value:
            show_snackbar("Batch name is required!", True)
            return

        if edit_batch_id is None:
            if add_batch(batch_name_field.value):
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
                    UPDATE batches SET name = ?
                    WHERE id = ?
                """, (batch_name_field.value, edit_batch_id))
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
        hint_text="Search by name",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        on_change=lambda e: update_batch_list(),
    )

    batch_list_view = ft.ListView(spacing=10, padding=20, expand=True)

    def update_batch_list():
        """Update the batch list display."""
        query = search_field.value or ""
        batches = get_all_batches()

        if query:
            batches = [b for b in batches if query.lower() in b.name.lower()]

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
                                    ]),
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
        save_button.text = "Update Batch"
        save_button.icon = ft.Icons.UPDATE
        page.update()

    def clear_batch_form():
        """Clear batch form fields."""
        nonlocal edit_batch_id
        edit_batch_id = None
        batch_name_field.value = ""
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

        def save_quick(e):
            if name_field.value:
                if add_batch(name_field.value):
                    update_batch_list()
                    show_snackbar("Batch added successfully!")
                    dlg.open = False
                    page.update()
                else:
                    show_snackbar("Error adding batch! Name may already exist.", True)
            else:
                show_snackbar("Batch name is required!", True)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add New Batch"),
            content=ft.Container(
                content=name_field,
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
            ft.Text("Manage academic year batches", size=12, color=ft.Colors.GREY_600),
            ft.Divider(),
            search_field,
            ft.Container(
                content=ft.Column([
                    ft.Text("Add / Edit Batch", size=14, weight=ft.FontWeight.W_500),
                    ft.Row([
                        batch_name_field,
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
