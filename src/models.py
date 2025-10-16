from typing import Optional


class Batch:
    """Batch data model."""
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name


class Student:
    """Student data model."""
    def __init__(self, id: int, name: str, age: int,
                  batch_id: Optional[int] = None, batch_name: str = "",
                  class_id: Optional[int] = None, class_name: str = ""):
        self.id = id
        self.name = name
        self.age = age
        self.batch_id = batch_id
        self.batch_name = batch_name
        self.class_id = class_id
        self.class_name = class_name


class Class:
    """Class data model."""
    def __init__(self, id: int, name: str, start_time: str = "", end_time: str = "",
                 recurrence_pattern: int = 127, start_date: Optional[str] = None,
                 end_date: Optional[str] = None):
        self.id = id
        self.name = name
        self.start_time = start_time
        self.end_time = end_time
        self.recurrence_pattern = recurrence_pattern
        self.start_date = start_date
        self.end_date = end_date


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


class FeeTemplate:
    """Fee template data model."""
    def __init__(self, id: int, name: str, description: str, amount: float,
                 frequency: str, batch_id: Optional[int] = None, batch_name: str = "",
                 is_active: bool = True, created_at: str = ""):
        self.id = id
        self.name = name
        self.description = description
        self.amount = amount
        self.frequency = frequency
        self.batch_id = batch_id
        self.batch_name = batch_name
        self.is_active = is_active
        self.created_at = created_at
