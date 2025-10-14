"""
Database operations for School Management System
"""
import sqlite3
from typing import List, Optional
from models import Student, Class, AttendanceRecord, FeeRecord
from datetime import date

# Database configuration
DB_PATH = "school.db"


def init_db():
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            grade TEXT NOT NULL,
            class_id INTEGER,
            FOREIGN KEY (class_id) REFERENCES classes (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Late')),
            FOREIGN KEY (student_id) REFERENCES students (id),
            UNIQUE(student_id, date)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL,
            paid_date TEXT,
            status TEXT NOT NULL CHECK(status IN ('Pending', 'Paid')),
            description TEXT,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')

    # Create face_encodings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS face_encodings (
            student_id INTEGER PRIMARY KEY,
            encoding   BLOB NOT NULL,
            updated_at TEXT  NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        )
    ''')

    # Create default admin user
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password) VALUES ('admin', 'admin123')")

    conn.commit()
    conn.close()


def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Class operations
def get_all_classes() -> List[Class]:
    """Retrieve all classes from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY name")
    classes = [Class(row['id'], row['name']) for row in cursor.fetchall()]
    conn.close()
    return classes


def add_class(name: str) -> bool:
    """Add a new class to database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO classes (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


# Student operations
def get_all_students(search_query: str = "") -> List[Student]:
    """Retrieve all students, optionally filtered by search query."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if search_query:
        query = """
            SELECT s.id, s.name, s.age, s.grade, s.class_id, c.name as class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.name LIKE ? OR s.grade LIKE ? OR c.name LIKE ?
            ORDER BY s.name
        """
        search_term = f"%{search_query}%"
        cursor.execute(query, (search_term, search_term, search_term))
    else:
        query = """
            SELECT s.id, s.name, s.age, s.grade, s.class_id, c.name as class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            ORDER BY s.name
        """
        cursor.execute(query)

    students = []
    for row in cursor.fetchall():
        students.append(Student(
            row['id'],
            row['name'],
            row['age'],
            row['grade'],
            row['class_id'],
            row['class_name'] or ""
        ))
    conn.close()
    return students


def get_student_by_id(student_id: int) -> Optional[Student]:
    """Get a single student by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.name, s.age, s.grade, s.class_id, c.name as class_name
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE s.id = ?
    """, (student_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return Student(
            row['id'],
            row['name'],
            row['age'],
            row['grade'],
            row['class_id'],
            row['class_name'] or ""
        )
    return None


def add_student(name: str, age: int, grade: str, class_id: Optional[int]) -> bool:
    """Add a new student to database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (name, age, grade, class_id) VALUES (?, ?, ?, ?)",
            (name, age, grade, class_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def update_student(student_id: int, name: str, age: int, grade: str,
                   class_id: Optional[int]) -> bool:
    """Update an existing student."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE students SET name = ?, age = ?, grade = ?, class_id = ? WHERE id = ?",
            (name, age, grade, class_id, student_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def delete_student(student_id: int) -> bool:
    """Delete a student and all related records."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fees WHERE student_id = ?", (student_id,))
        cursor.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# Attendance operations
def get_attendance_for_student(student_id: int, start_date: str,
                               end_date: str) -> List[AttendanceRecord]:
    """Get attendance records for a student within date range."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM attendance
        WHERE student_id = ? AND date BETWEEN ? AND ?
        ORDER BY date DESC
    """, (student_id, start_date, end_date))
    records = [AttendanceRecord(row['student_id'], row['date'], row['status'])
               for row in cursor.fetchall()]
    conn.close()
    return records


def update_attendance(student_id: int, date_str: str, status: str) -> bool:
    """Update or insert attendance record."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO attendance (student_id, date, status)
            VALUES (?, ?, ?)
            ON CONFLICT(student_id, date) DO UPDATE SET status = excluded.status
        """, (student_id, date_str, status))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# Fee operations
def get_fees_for_student(student_id: int) -> List[FeeRecord]:
    """Get all fee records for a student."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM fees
        WHERE student_id = ?
        ORDER BY due_date DESC
    """, (student_id,))
    records = [FeeRecord(
        row['id'],
        row['student_id'],
        row['amount'],
        row['due_date'],
        row['paid_date'],
        row['status'],
        row['description'] or ""
    ) for row in cursor.fetchall()]
    conn.close()
    return records


def add_fee_record(student_id: int, amount: float, due_date: str,
                   description: str) -> bool:
    """Add a new fee record."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fees (student_id, amount, due_date, status, description)
            VALUES (?, ?, ?, 'Pending', ?)
        """, (student_id, amount, due_date, description))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def update_fee_status(fee_id: int, status: str) -> bool:
    """Update fee payment status."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        paid_date = str(date.today()) if status == 'Paid' else None
        cursor.execute("""
            UPDATE fees
            SET status = ?, paid_date = ?
            WHERE id = ?
        """, (status, paid_date, fee_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def delete_fee_record(fee_id: int) -> bool:
    """Delete a fee record."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fees WHERE id = ?", (fee_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# Authentication
def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user credentials."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?",
                  (username, password))
    result = cursor.fetchone()
    conn.close()
    return result is not None
