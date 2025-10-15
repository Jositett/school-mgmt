import flet as ft
from datetime import date
from database import get_fees_for_student, add_fee_record, update_fee_status, delete_fee_record
from models import FeeRecord


def create_fees_view(page: ft.Page, show_snackbar, selected_student_for_fees):
    """Create the fees management view."""
    student_dropdown = ft.Dropdown(
        label="Select Student",
        hint_text="Choose a student",
        # No icon for dropdown
        on_change=lambda e: load_fees_records(),
        expand=True,
    )

    amount_field = ft.TextField(
        label="Amount",
        hint_text="Enter amount",
        prefix_icon=ft.Icons.MONETIZATION_ON,
        width=150,
        input_filter=ft.NumbersOnlyInputFilter(),
    )

    due_date_field = ft.TextField(
        label="Due Date",
        value=str(date.today()),
        prefix_icon=ft.Icons.CALENDAR_TODAY,
        width=200,
        read_only=True,
    )

    description_field = ft.TextField(
        label="Description",
        hint_text="Optional description",
        prefix_icon=ft.Icons.DESCRIPTION,
        expand=True,
    )

    fees_list_view = ft.ListView(
        spacing=10,
        padding=20,
        expand=True,
    )

    def load_students():
        """Load all students into dropdown."""
        from database import get_all_students
        students = get_all_students()
        student_dropdown.options = [
            ft.dropdown.Option(key=str(s.id), text=f"{s.name} - Batch {s.batch_name}")
            for s in students
        ]
        if students:
            student_dropdown.value = str(students[0].id)
            selected_student_for_fees = students[0].id
        page.update()

    def load_fees_records():
        """Load fees records for selected student."""
        if not student_dropdown.value:
            return

        selected_student_for_fees = int(student_dropdown.value)
        records = get_fees_for_student(selected_student_for_fees)

        fees_list_view.controls.clear()

        if not records:
            fees_list_view.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.RECEIPT_LONG, size=64, color=ft.Colors.GREY_400),
                        ft.Text("No fee records found", size=16, color=ft.Colors.GREY_600),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=40,
                )
            )
        else:
            total_pending = 0
            total_paid = 0

            for record in records:
                if record.status == "Paid":
                    total_paid += record.amount
                else:
                    total_pending += record.amount

                status_color = ft.Colors.GREEN_700 if record.status == "Paid" else ft.Colors.RED_700

                fees_list_view.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(f"${record.amount:.2f}", weight=ft.FontWeight.BOLD, size=16),
                                    ft.Text(record.status, color=status_color, size=12),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Row([
                                    ft.Icon(ft.Icons.CALENDAR_TODAY, size=14, color=ft.Colors.GREY_600),
                                    ft.Text(f"Due: {record.due_date}", size=12, color=ft.Colors.GREY_600),
                                    ft.VerticalDivider(width=1),
                                    ft.Icon(ft.Icons.PAYMENT, size=14, color=ft.Colors.GREY_600),
                                    ft.Text(f"Paid: {record.paid_date or 'N/A'}", size=12, color=ft.Colors.GREY_600),
                                ], spacing=5),
                                ft.Text(record.description or "", size=12, color=ft.Colors.GREY_700),
                                ft.Row([
                                    ft.IconButton(
                                        icon=ft.Icons.PAYMENT,
                                        icon_color=ft.Colors.BLUE_700,
                                        tooltip="Mark as Paid",
                                        on_click=lambda e, r=record: mark_fee_paid(r),
                                        disabled=record.status == "Paid",
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED_700,
                                        tooltip="Delete",
                                        on_click=lambda e, fid=record.id: confirm_delete_fee(fid),
                                    ),
                                ], spacing=0),
                            ], spacing=5),
                            padding=15,
                        ),
                    )
                )

            # Add summary card
            fees_list_view.controls.insert(
                0,
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("Fee Summary", weight=ft.FontWeight.BOLD, size=16),
                            ft.Divider(height=10),
                            ft.Row([
                                ft.Column([
                                    ft.Text("Total Pending:", size=14, color=ft.Colors.RED_700),
                                    ft.Text(f"${total_pending:.2f}", weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.RED_700),
                                ]),
                                ft.VerticalDivider(width=1),
                                ft.Column([
                                    ft.Text("Total Paid:", size=14, color=ft.Colors.GREEN_700),
                                    ft.Text(f"${total_paid:.2f}", weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.GREEN_700),
                                ]),
                                ft.VerticalDivider(width=1),
                                ft.Column([
                                    ft.Text("Total Fees:", size=14),
                                    ft.Text(f"${(total_pending + total_paid):.2f}", weight=ft.FontWeight.BOLD, size=16),
                                ]),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ], spacing=10),
                        padding=15,
                    ),
                )
            )
        page.update()

    def mark_fee_paid(record: FeeRecord):
        """Mark a fee as paid."""
        if update_fee_status(record.id, "Paid"):
            show_snackbar("Fee marked as paid!")
            load_fees_records()
        else:
            show_snackbar("Error updating fee status!", True)

    def confirm_delete_fee(fee_id: int):
        """Show confirmation dialog for deleting fee."""
        def delete_confirmed(e):
            if delete_fee_record(fee_id):
                show_snackbar("Fee record deleted!")
                load_fees_records()
            else:
                show_snackbar("Error deleting fee record!", True)
            dialog.open = False
            page.update()

        def cancel_delete(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete"),
            content=ft.Text("Are you sure you want to delete this fee record?"),
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

    def save_fee(e):
        """Save a new fee record."""
        if selected_student_for_fees is None:
            show_snackbar("Please select a student!", True)
            return

        if not amount_field.value or not due_date_field.value:
            show_snackbar("Amount and Due Date are required!", True)
            return

        try:
            amount = float(amount_field.value)
            if amount <= 0:
                show_snackbar("Amount must be positive!", True)
                return

            if add_fee_record(
                selected_student_for_fees,
                amount,
                due_date_field.value,
                description_field.value or ""
            ):
                show_snackbar("Fee record added successfully!")
                # Reset form
                amount_field.value = ""
                description_field.value = ""
                due_date_field.value = str(date.today())
                load_fees_records()
            else:
                show_snackbar("Error adding fee record!", True)
        except ValueError:
            show_snackbar("Invalid amount value!", True)

    def open_calendar(e):
        """Open date picker dialog."""
        def handle_date_change(e):
            due_date_field.value = e.control.value.strftime("%Y-%m-%d")
            page.update()

        date_picker = ft.DatePicker(
            on_change=handle_date_change,
            first_date=date(2020, 1, 1),
            last_date=date(2030, 12, 31),
        )
        page.overlay.append(date_picker)
        date_picker.open = True
        page.update()

    # Make date field clickable to open calendar
    due_date_field.on_click = open_calendar

    # Initialize
    load_students()
    if student_dropdown.value:
        load_fees_records()

    # Build view
    return ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Text("Fees Management", size=24, weight=ft.FontWeight.BOLD),
                padding=20,
            ),
            ft.Divider(height=1),
            ft.Container(
                content=ft.Column([
                    ft.Text("Add Fee Record", size=16, weight=ft.FontWeight.W_500),
                    student_dropdown,
                    ft.Row([
                        amount_field,
                        due_date_field,
                    ], spacing=15),
                    description_field,
                    ft.ElevatedButton(
                        "Add Fee Record",
                        icon=ft.Icons.ADD,
                        on_click=save_fee,
                    ),
                ], spacing=15),
                padding=20,
            ),
            ft.Divider(height=1),
            ft.Container(
                content=ft.Column([
                    ft.Text("Fee Records", size=16, weight=ft.FontWeight.W_500),
                    ft.Container(
                        content=fees_list_view,
                        expand=True,
                    ),
                ], spacing=10),
                padding=20,
                expand=True,
            ),
        ], spacing=0, expand=True),
        expand=True,
    )
