"""
Utility functions for School Management System
"""
import csv
from datetime import datetime, date, timedelta
import flet as ft
from models import Student
from database import get_all_students, export_students_to_csv


def export_students_to_csv():
    """Export all students to CSV file."""
    students = get_all_students()
    filename = f"students_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'Name', 'Age', 'Grade', 'Class'])
        for student in students:
            writer.writerow([student.id, student.name, student.age,
                           student.grade, student.class_name])
    return filename


def show_snackbar(page: ft.Page, message: str, is_error: bool = False):
    """Show snackbar notification."""
    page.snack_bar = ft.SnackBar(
        content=ft.Text(message),
        bgcolor=ft.Colors.RED_400 if is_error else ft.Colors.GREEN_400,
    )
    page.snack_bar.open = True
    page.update()
