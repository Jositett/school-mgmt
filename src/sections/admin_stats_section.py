"""
Admin statistics section for the school management system.

This module contains the statistics header section extracted from admin_view.py
for better organization and reusability.
"""

import flet as ft
import sqlite3
from database import get_all_students, get_all_batches, get_all_classes
from sections.admin_utils import ResponsiveCard, ResponsiveRow, get_breakpoint


def get_stats_section(page):
    """Create statistics header section with counts for students, classes, batches, and face data."""
    try:
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