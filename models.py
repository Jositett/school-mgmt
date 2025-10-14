from typing import Optional


class Student:
    """Student data model."""
    def __init__(self, id: int, name: str, age: int, grade: str,
                  class_id: Optional[int] = None, class_name: str = ""):
        self.id = id
        self.name = name
        self.age = age
        self.grade = grade
        self.class_id = class_id
        self.class_name = class_name


class Class:
    """Class data model."""
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name


class AttendanceRecord:
    """Attendance record data model."""
    def __init__(self, student_id: int, date: str, status: str):
        self.student_id = student_id
        self.date = date
        self.status = status


class FeeRecord:
    """Fee record data model."""
    def __init__(self, id: int, student_id: int, amount: float, due_date: str,
                  paid_date: Optional[str], status: str, description: str):
        self.id = id
        self.student_id = student_id
        self.amount = amount
        self.due_date = due_date
        self.paid_date = paid_date
        self.status = status
        self.description = description