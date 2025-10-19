"""
Views module for School Management System.

This module contains all UI view functions organized by feature.
"""

from .student_view import create_student_view
from .attendance_view import create_attendance_view
from .fees_view import create_fees_view
from .face_enrollment_view import create_enrol_face_view  # Use improved version with responsive design
from .live_attendance_view import create_live_attendance_view
from .admin_view import create_admin_view

__all__ = [
    'create_student_view',
    'create_attendance_view',
    'create_fees_view',
    'create_enrol_face_view',
    'create_live_attendance_view',
    'create_admin_view',
]
