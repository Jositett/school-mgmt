import os, pickle, datetime, pathlib, requests, base64, time, threading
import flet as ft
import sqlite3
import cv2
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Optional
from utils import export_students_to_csv

# Import face_recognition with proper error handling
# Silence the import error by redirecting stderr
import sys
from io import StringIO

old_stderr = sys.stderr  # Store original stderr
redirected_stderr = StringIO()
sys.stderr = redirected_stderr

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError as e:
    FACE_RECOGNITION_AVAILABLE = False
    print(f"Face recognition module not available: {e}")
    print("Face recognition features will be disabled.")
    # Create a mock face_recognition module to prevent errors
    face_recognition = None

sys.stderr = old_stderr  # Restore stderr

# Database setup
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


# Data models
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


MODEL_DIR = pathlib.Path("models")
MODEL_DIR.mkdir(exist_ok=True)
LANDMARKS = MODEL_DIR / "shape_predictor_68_face_landmarks.dat"

# one-time download
if not LANDMARKS.exists():
    print("Downloading face landmark model …")
    url = "https://github.com/AKSHAYUBHAT/face_recognition/raw/master/models/shape_predictor_68_face_landmarks.dat"
    open(LANDMARKS,"wb").write(requests.get(url).content)


class FaceService:
    """Singleton that keeps one in-memory copy of all encodings."""
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_encodings()
        return cls._instance

    # ---------- public API ----------
    def enrol_student(self, student_id: int, images_or_video: list[cv2.Mat]) -> bool:
        """Pass either a list of cv2 images or a list with one video frame every 200 ms."""
        encodings = []
        for frame in images_or_video:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes = face_recognition.face_locations(rgb, model="hog")  # or "cnn" if GPU
            if boxes:
                encodings.append(face_recognition.face_encodings(rgb, boxes)[0])
        if len(encodings) < 1:
            return False
        mean_encoding = np.mean(encodings, axis=0)                   # simple average
        self._save_encoding(student_id, mean_encoding)
        self._load_encodings()                                       # refresh RAM
        return True

    def recognise(self, frame: cv2.Mat) -> list[tuple[int, float]]:
        """Return [(student_id, distance), …] for all faces in frame (distance ≤ 0.45)."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(rgb, model="hog")
        if not boxes:
            return []
        unknown_encodings = face_recognition.face_encodings(rgb, boxes)
        results = []
        for enc in unknown_encodings:
            distances = face_recognition.face_distance(self.known_encodings, enc)
            best_idx = np.argmin(distances)
            if distances[best_idx] <= 0.45:          # tune threshold if needed
                results.append((self.known_ids[best_idx], float(distances[best_idx])))
        return results

    # ---------- internal ----------
    def _load_encodings(self):
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT student_id, encoding FROM face_encodings").fetchall()
        conn.close()
        self.known_ids = [r[0] for r in rows]
        self.known_encodings = [np.frombuffer(r[1], dtype=np.float32) for r in rows]

    def _save_encoding(self, student_id: int, enc: np.ndarray):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO face_encodings(student_id, encoding, updated_at) VALUES (?,?,?)",
            (student_id, enc.tobytes(), datetime.now().isoformat()))
        conn.commit()
        conn.close()


# Database operations
def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user credentials."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                  (username, password))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def main(page: ft.Page):
    """Main application entry point."""
    # Configure page
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.title = "School Management System"
    page.window.width = 1200
    page.window.height = 800
    page.window.min_width = 800
    page.window.min_height = 600
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO
    
    # Modern color scheme
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.BLUE,
        use_material3=True,
    )
    
    # State variables
    current_user = None
    edit_student_id = None
    current_view = "students"
    selected_student_for_attendance = None
    selected_student_for_fees = None
    
    # Create UI components
    def create_app_bar():
        """Create modern app bar."""
        return ft.AppBar(
            title=ft.Text("School Management System", weight=ft.FontWeight.BOLD),
            center_title=False,
            bgcolor=ft.Colors.BLUE_700,
            actions=[
                ft.PopupMenuButton(
                    items=[
                        ft.PopupMenuItem(
                            text=f"Logged in as: {current_user}",
                            disabled=True,
                        ),
                        ft.PopupMenuItem(),
                        ft.PopupMenuItem(
                            text="Logout",
                            icon=ft.Icons.LOGOUT,
                            on_click=logout,
                        ),
                    ],
                    icon=ft.Icons.ACCOUNT_CIRCLE,
                    icon_color=ft.Colors.WHITE,
                ),
            ],
        )
    
    def create_navigation_rail():
        """Create modern navigation rail."""
        return ft.NavigationRail(
            selected_index=0 if current_view == "students" else 1 if current_view == "enrol_face" else 2 if current_view == "live_attendance" else 3 if current_view == "fees" else 0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.PEOPLE_OUTLINE,
                    selected_icon=ft.Icons.PEOPLE,
                    label="Students",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PHOTO_CAMERA_OUTLINED,
                    selected_icon=ft.Icons.PHOTO_CAMERA,
                    label="Enrol Face",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.FACE_OUTLINED,
                    selected_icon=ft.Icons.FACE,
                    label="Live Attendance",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PAYMENTS_OUTLINED,
                    selected_icon=ft.Icons.PAYMENTS,
                    label="Fees",
                ),
            ],
            on_change=lambda e: change_view(e.control.selected_index),
        )
    
    def change_view(index: int):
        """Change the current view based on navigation selection."""
        nonlocal current_view
        if index == 0:
            current_view = "students"
        elif index == 1:
            current_view = "enrol_face"
        elif index == 2:
            current_view = "live_attendance"
        elif index == 3:
            current_view = "attendance"
        elif index == 4:
            current_view = "fees"
        else:
            current_view = "students"
        show_main_app()
    
    def show_snackbar(message: str, is_error: bool = False):
        """Show snackbar notification."""
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.RED_400 if is_error else ft.Colors.GREEN_400,
        )
        page.snack_bar.open = True
        page.update()
    
    # Student Management View
    def create_student_view():
        """Create the student management view."""
        nonlocal edit_student_id
        
        # Form fields - Use prefix_icon (works in 0.28.3 despite deprecation warning)
        name_field = ft.TextField(
            label="Student Name",
            hint_text="Enter full name",
            prefix_icon=ft.Icons.PERSON,
            expand=True,
        )
        
        age_field = ft.TextField(
            label="Age",
            hint_text="5-18",
            prefix_icon=ft.Icons.CAKE,
            width=120,
            input_filter=ft.NumbersOnlyInputFilter(),
        )
        
        grade_field = ft.TextField(
            label="Grade",
            hint_text="e.g., 10th",
            prefix_icon=ft.Icons.SCHOOL,
            width=150,
        )
        
        class_dropdown = ft.Dropdown(
            label="Class",
            hint_text="Select class",
            # No icon for dropdown in 0.28.3
            width=200,
        )
        
        search_field = ft.TextField(
            label="Search",
            hint_text="Search by name, grade, or class",
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: update_student_list(),
            expand=True,
        )
        
        student_list_view = ft.ListView(
            spacing=10,
            padding=20,
            expand=True,
        )
        
        def load_classes():
            """Load classes into dropdown."""
            classes = get_all_classes()
            class_dropdown.options = [
                ft.dropdown.Option(key=str(c.id), text=c.name) for c in classes
            ]
            if classes:
                class_dropdown.value = str(classes[0].id)
        
        def update_student_list():
            """Update the student list display."""
            students = get_all_students(search_field.value)
            student_list_view.controls.clear()
            
            if not students:
                student_list_view.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.GREY_400),
                            ft.Text("No students found", size=16, color=ft.Colors.GREY_600),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=40,
                    )
                )
            else:
                for student in students:
                    student_list_view.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.CircleAvatar(
                                            content=ft.Text(
                                                student.name[0].upper(),
                                                size=20,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            bgcolor=ft.Colors.BLUE_200,
                                            color=ft.Colors.BLUE_900,
                                        ),
                                        width=50,
                                    ),
                                    ft.Column([
                                        ft.Text(student.name, weight=ft.FontWeight.BOLD, size=16),
                                        ft.Row([
                                            ft.Icon(ft.Icons.CAKE, size=16, color=ft.Colors.GREY_600),
                                            ft.Text(f"{student.age} years", size=12, color=ft.Colors.GREY_600),
                                            ft.VerticalDivider(width=1),
                                            ft.Icon(ft.Icons.SCHOOL, size=16, color=ft.Colors.GREY_600),
                                            ft.Text(f"Grade {student.grade}", size=12, color=ft.Colors.GREY_600),
                                            ft.VerticalDivider(width=1),
                                            ft.Icon(ft.Icons.CLASS_, size=16, color=ft.Colors.GREY_600),
                                            ft.Text(student.class_name or "No class", size=12, color=ft.Colors.GREY_600),
                                        ], spacing=5),
                                    ], spacing=5, expand=True),
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT,
                                            icon_color=ft.Colors.BLUE_700,
                                            tooltip="Edit",
                                            on_click=lambda e, s=student: edit_student(s),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.CALENDAR_TODAY,
                                            icon_color=ft.Colors.GREEN_700,
                                            tooltip="Attendance",
                                            on_click=lambda e, s=student: open_attendance_for_student(s),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.PAYMENTS,
                                            icon_color=ft.Colors.ORANGE_700,
                                            tooltip="Fees",
                                            on_click=lambda e, s=student: open_fees_for_student(s),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            icon_color=ft.Colors.RED_700,
                                            tooltip="Delete",
                                            on_click=lambda e, sid=student.id: confirm_delete_student(sid),
                                        ),
                                    ], spacing=0),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                padding=15,
                            ),
                        )
                    )
            page.update()
        
        def edit_student(student: Student):
            """Load student data for editing."""
            nonlocal edit_student_id
            edit_student_id = student.id
            name_field.value = student.name
            age_field.value = str(student.age)
            grade_field.value = student.grade
            class_dropdown.value = str(student.class_id) if student.class_id else None
            page.update()
        
        def clear_form():
            """Clear all form fields."""
            nonlocal edit_student_id
            edit_student_id = None
            name_field.value = ""
            age_field.value = ""
            grade_field.value = ""
            load_classes()
            page.update()
        
        def save_student(e):
            """Save or update student."""
            nonlocal edit_student_id
            
            if not name_field.value or not age_field.value or not grade_field.value:
                show_snackbar("All fields are required!", True)
                return
            
            try:
                age = int(age_field.value)
                if age < 5 or age > 18:
                    show_snackbar("Age must be between 5 and 18!", True)
                    return
                
                class_id = int(class_dropdown.value) if class_dropdown.value else None
                
                if edit_student_id is None:
                    if add_student(name_field.value, age, grade_field.value, class_id):
                        show_snackbar("Student added successfully!")
                        clear_form()
                        update_student_list()
                    else:
                        show_snackbar("Error adding student!", True)
                else:
                    if update_student(edit_student_id, name_field.value, age, 
                                    grade_field.value, class_id):
                        show_snackbar("Student updated successfully!")
                        clear_form()
                        update_student_list()
                    else:
                        show_snackbar("Error updating student!", True)
            except ValueError:
                show_snackbar("Invalid age value!", True)
        
        def confirm_delete_student(student_id: int):
            """Show confirmation dialog for deleting student."""
            def delete_confirmed(e):
                if delete_student(student_id):
                    show_snackbar("Student deleted successfully!")
                    update_student_list()
                else:
                    show_snackbar("Error deleting student!", True)
                dialog.open = False
                page.update()
            
            def cancel_delete(e):
                dialog.open = False
                page.update()
            
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirm Delete"),
                content=ft.Text("Are you sure you want to delete this student? All attendance and fee records will also be deleted."),
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
        
        def export_csv(e):
            """Export students to CSV."""
            try:
                filename = export_students_to_csv()
                show_snackbar(f"Exported to: {filename}")
            except Exception as ex:
                show_snackbar(f"Export failed: {str(ex)}", True)
        
        def add_class_dialog(e):
            """Show dialog to add new class."""
            class_name_field = ft.TextField(
                label="Class Name",
                hint_text="e.g., Grade 10A",
                autofocus=True,
            )
            
            def save_class(e):
                if class_name_field.value and add_class(class_name_field.value):
                    load_classes()
                    show_snackbar("Class added successfully!")
                    dialog.open = False
                    page.update()
                else:
                    show_snackbar("Error adding class! Name might be duplicate.", True)
            
            def close_dialog(e):
                dialog.open = False
                page.update()
            
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Add New Class"),
                content=ft.Container(
                    content=class_name_field,
                    width=300,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=close_dialog),
                    ft.TextButton("Add", on_click=save_class),
                ],
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()
        
        # Initialize
        load_classes()
        update_student_list()
        
        # Build view
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text("Student Management", size=24, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.ElevatedButton(
                                "Export CSV",
                                icon=ft.Icons.DOWNLOAD,
                                on_click=export_csv,
                            ),
                        ]),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=20,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Column([
                        search_field,
                        ft.Text("Add / Edit Student", size=16, weight=ft.FontWeight.W_500),
                        ft.Row([
                            name_field,
                        ]),
                        ft.Row([
                            age_field,
                            grade_field,
                            class_dropdown,
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE,
                                icon_color=ft.Colors.GREEN_700,
                                tooltip="Add New Class",
                                on_click=add_class_dialog,
                            ),
                        ]),
                        ft.Row([
                            ft.ElevatedButton(
                                "Save Student" if edit_student_id is None else "Update Student",
                                icon=ft.Icons.SAVE,
                                on_click=save_student,
                            ),
                            ft.OutlinedButton(
                                "Clear",
                                icon=ft.Icons.CLEAR,
                                on_click=lambda e: clear_form(),
                            ),
                        ]),
                    ], spacing=15),
                    padding=20,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Students List", size=16, weight=ft.FontWeight.W_500),
                        ft.Container(
                            content=student_list_view,
                            expand=True,
                        ),
                    ], spacing=10),
                    padding=20,
                    expand=True,
                ),
            ], spacing=0, expand=True),
            expand=True,
        )
    
    # Attendance Management View
    def create_attendance_view():
        """Create the attendance management view."""
        nonlocal selected_student_for_attendance
        
        student_dropdown = ft.Dropdown(
            label="Select Student",
            hint_text="Choose a student",
            # No icon for dropdown
            on_change=lambda e: load_attendance_records(),
            expand=True,
        )
        
        date_picker_field = ft.TextField(
            label="Date",
            value=str(date.today()),
            prefix_icon=ft.Icons.CALENDAR_TODAY,
            width=200,
            read_only=True,
        )
        
        status_dropdown = ft.Dropdown(
            label="Status",
            # No icon for dropdown
            width=200,
            options=[
                ft.dropdown.Option("Present"),
                ft.dropdown.Option("Absent"),
                ft.dropdown.Option("Late"),
            ],
            value="Present",
        )
        
        attendance_list_view = ft.ListView(
            spacing=10,
            padding=20,
            expand=True,
        )
        
        def load_students():
            """Load all students into dropdown."""
            students = get_all_students()
            student_dropdown.options = [
                ft.dropdown.Option(key=str(s.id), text=f"{s.name} - Grade {s.grade}")
                for s in students
            ]
            if students:
                student_dropdown.value = str(students[0].id)
                selected_student_for_attendance = students[0].id
            page.update()
        
        def load_attendance_records():
            """Load attendance records for selected student."""
            nonlocal selected_student_for_attendance
            
            if not student_dropdown.value:
                return
            
            selected_student_for_attendance = int(student_dropdown.value)
            start_date = str((date.today() - timedelta(days=30)))
            end_date = str(date.today())
            
            records = get_attendance_for_student(
                selected_student_for_attendance,
                start_date,
                end_date
            )
            
            attendance_list_view.controls.clear()
            
            if not records:
                attendance_list_view.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.EVENT_BUSY, size=64, color=ft.Colors.GREY_400),
                            ft.Text("No attendance records found", size=16, color=ft.Colors.GREY_600),
                            ft.Text("(Last 30 days)", size=12, color=ft.Colors.GREY_500),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=40,
                    )
                )
            else:
                for record in records:
                    status_color = {
                        "Present": ft.Colors.GREEN_700,
                        "Absent": ft.Colors.RED_700,
                        "Late": ft.Colors.ORANGE_700,
                    }.get(record.status, ft.Colors.GREY_700)
                    
                    attendance_list_view.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Row([
                                    ft.Column([
                                        ft.Text(record.date, weight=ft.FontWeight.BOLD),
                                        ft.Text(record.status, color=status_color, size=12),
                                    ]),
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        icon_color=ft.Colors.BLUE_700,
                                        tooltip="Edit",
                                        on_click=lambda e, r=record: edit_attendance_record(r),
                                    ),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                padding=15,
                            ),
                        )
                    )
            page.update()
        
        def edit_attendance_record(record: AttendanceRecord):
            """Edit an attendance record."""
            date_picker_field.value = record.date
            status_dropdown.value = record.status
            page.update()
        
        def save_attendance(e):
            """Save attendance record."""
            nonlocal selected_student_for_attendance
            
            if selected_student_for_attendance is None:
                show_snackbar("Please select a student!", True)
                return
            
            if not date_picker_field.value or not status_dropdown.value:
                show_snackbar("Please fill all fields!", True)
                return
            
            if update_attendance(
                selected_student_for_attendance,
                date_picker_field.value,
                status_dropdown.value
            ):
                show_snackbar("Attendance updated successfully!")
                load_attendance_records()
                # Reset form
                date_picker_field.value = str(date.today())
                status_dropdown.value = "Present"
                page.update()
            else:
                show_snackbar("Error updating attendance!", True)
        
        def open_calendar(e):
            """Open date picker dialog."""
            def handle_date_change(e):
                date_picker_field.value = e.control.value.strftime("%Y-%m-%d")
                page.update()
            
            date_picker = ft.DatePicker(
                on_change=handle_date_change,
                first_date=date(2020, 1, 1),
                last_date=date(2030, 12, 31),
            )
            page.overlay.append(date_picker)
            page.update()
            date_picker.pick_date()
        
        # Make date field clickable to open calendar
        date_picker_field.on_click = open_calendar
        
        # Initialize
        load_students()
        if student_dropdown.value:
            load_attendance_records()
        
        # Build view
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text("Attendance Management", size=24, weight=ft.FontWeight.BOLD),
                    padding=20,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Record Attendance", size=16, weight=ft.FontWeight.W_500),
                        student_dropdown,
                        ft.Row([
                            date_picker_field,
                            status_dropdown,
                            ft.ElevatedButton(
                                "Save Attendance",
                                icon=ft.Icons.SAVE,
                                on_click=save_attendance,
                            ),
                        ], spacing=15),
                    ], spacing=15),
                    padding=20,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Recent Attendance Records (Last 30 Days)", size=16, weight=ft.FontWeight.W_500),
                        ft.Container(
                            content=attendance_list_view,
                            expand=True,
                        ),
                    ], spacing=10),
                    padding=20,
                    expand=True,
                ),
            ], spacing=0, expand=True),
            expand=True,
        )
    
    # Fees Management View
    def create_fees_view():
        """Create the fees management view."""
        nonlocal selected_student_for_fees
        
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
            students = get_all_students()
            student_dropdown.options = [
                ft.dropdown.Option(key=str(s.id), text=f"{s.name} - Grade {s.grade}")
                for s in students
            ]
            if students:
                student_dropdown.value = str(students[0].id)
                selected_student_for_fees = students[0].id
            page.update()
        
        def load_fees_records():
            """Load fees records for selected student."""
            nonlocal selected_student_for_fees
            
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
            nonlocal selected_student_for_fees
            
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
                    description_field.value
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
            page.update()
            date_picker.pick_date()
        
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
    
    # Helper functions for navigation
    def open_attendance_for_student(student: Student):
        """Open attendance view for a specific student."""
        nonlocal current_view, selected_student_for_attendance
        current_view = "attendance"
        selected_student_for_attendance = student.id
        show_main_app()
    
    def open_fees_for_student(student: Student):
        """Open fees view for a specific student."""
        nonlocal current_view, selected_student_for_fees
        current_view = "fees"
        selected_student_for_fees = student.id
        show_main_app()
    
    # Face Enrollment View
    def create_enrol_face_view():
        """Create face enrolment view."""
        student_dropdown = ft.Dropdown(
            label="Select Student",
            hint_text="Choose student to enrol face",
            width=400,
        )

        capture_btn = ft.ElevatedButton(
            "Start Webcam Enrolment",
            icon=ft.Icons.VIDEOCAM,
            on_click=lambda e: enrol_student_face(),
        )

        status_text = ft.Text("", size=14)

        def load_students():
            """Load students into dropdown."""
            students = get_all_students()
            student_dropdown.options = [
                ft.dropdown.Option(key=str(s.id), text=s.name) for s in students
            ]
            if students:
                student_dropdown.value = str(students[0].id)

        def enrol_student_face():
            """Enrol student face using webcam."""
            if not student_dropdown.value:
                show_snackbar("Please select a student!", True)
                return

            student_id = int(student_dropdown.value)
            status_text.value = "Starting webcam... Hold still and look at camera."
            page.update()

            try:
                cap = cv2.VideoCapture(0)
                frames = []
                start_time = time.time()

                while len(frames) < 15 and (time.time() - start_time) < 5:  # Max 5 seconds
                    ret, frame = cap.read()
                    if not ret:
                        break
                    frames.append(frame)
                    time.sleep(0.2)  # 200ms intervals

                cap.release()

                if len(frames) < 5:
                    status_text.value = "Error: Not enough frames captured. Make sure webcam is working."
                    show_snackbar("Face enrolment failed!", True)
                else:
                    if FaceService().enrol_student(student_id, frames):
                        status_text.value = "Face enrolled successfully!"
                        show_snackbar("Face enrolled successfully!")
                    else:
                        status_text.value = "Error: No face detected. Try again with better lighting."
                        show_snackbar("Face enrolment failed!", True)

            except Exception as ex:
                status_text.value = f"Error: {str(ex)}"
                show_snackbar("Face enrolment failed!", True)

            page.update()

        load_students()

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text("Face Enrollment", size=24, weight=ft.FontWeight.BOLD),
                    padding=20,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Column([
                        student_dropdown,
                        ft.Container(height=20),
                        capture_btn,
                        ft.Container(height=20),
                        status_text,
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE_700),
                                ft.Text("• Make sure the webcam is working", size=12),
                                ft.Text("• Position face in center of frame", size=12),
                                ft.Text("• Ensure good lighting", size=12),
                                ft.Text("• Look directly at camera", size=12),
                            ], spacing=5),
                            padding=20,
                            border=ft.border.all(1, ft.Colors.GREY_300),
                            border_radius=10,
                        ),
                    ], spacing=15),
                    padding=20,
                ),
            ], spacing=0, expand=True),
            expand=True,
        )

    # Live Attendance View
    def create_live_attendance_view():
        """Create live face attendance view."""
        image_display = ft.Image(
            src_base64="",
            width=640,
            height=480,
            fit=ft.ImageFit.CONTAIN,
        )

        start_btn = ft.ElevatedButton(
            "Start Live Attendance",
            icon=ft.Icons.PLAY_ARROW,
        )

        stop_btn = ft.ElevatedButton(
            "Stop & Save Attendance",
            icon=ft.Icons.STOP,
            disabled=True,
        )

        status_text = ft.Text("Click 'Start Live Attendance' to begin", size=14)
        students_present = set()
        attendance_date = str(date.today())
        is_running = False

        def start_live_attendance(e):
            nonlocal is_running, students_present
            is_running = True
            students_present = set()
            start_btn.disabled = True
            stop_btn.disabled = False
            status_text.value = "Live attendance running... Students detected will be marked present."
            page.update()

            def capture_loop():
                nonlocal is_running
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    status_text.value = "Error: Cannot access webcam"
                    page.update()
                    return

                frame_count = 0
                while is_running:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Process every 10th frame to reduce CPU usage
                    if frame_count % 10 == 0:
                        faces = FaceService().recognise(frame)
                        if faces:
                            new_students = {student_id for student_id, _ in faces}
                            students_present.update(new_students)

                            # Update status with recognized students
                            student_names = []
                            for sid in new_students:
                                student = get_student_by_id(sid)
                                if student:
                                    student_names.append(student.name)
                            if student_names:
                                status_text.value = f"Recognized: {', '.join(student_names)}"

                    # Convert frame to base64 for display
                    _, buffer = cv2.imencode('.jpg', frame)
                    image_display.src_base64 = base64.b64encode(buffer).decode()
                    page.update()

                    frame_count += 1
                    time.sleep(0.1)  # ~10 FPS

                cap.release()

            # Run capture in thread to not block UI
            threading.Thread(target=capture_loop, daemon=True).start()

        def stop_live_attendance(e):
            nonlocal is_running, students_present, attendance_date
            is_running = False
            start_btn.disabled = False
            stop_btn.disabled = True

            # Mark attendance for all recognized students
            marked_count = 0
            for student_id in students_present:
                if update_attendance(student_id, attendance_date, "Present"):
                    marked_count += 1

            status_text.value = f"Attendance completed! Marked {marked_count} student(s) as present for {attendance_date}"
            image_display.src_base64 = ""
            show_snackbar(f"Marked {marked_count} student(s) present")
            page.update()

        start_btn.on_click = start_live_attendance
        stop_btn.on_click = stop_live_attendance

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text("Live Face Attendance", size=24, weight=ft.FontWeight.BOLD),
                    padding=20,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=image_display,
                            alignment=ft.alignment.center,
                            padding=20,
                        ),
                        ft.Row([
                            start_btn,
                            stop_btn,
                        ], spacing=15),
                        status_text,
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.SECURITY, color=ft.Colors.GREEN_700),
                                ft.Text("• Only students with enrolled faces will be recognized", size=12),
                                ft.Text("• Students will be marked as present automatically", size=12),
                                ft.Text("• Recognition works best with good lighting", size=12),
                            ], spacing=5),
                            padding=20,
                            border=ft.border.all(1, ft.Colors.GREY_300),
                            border_radius=10,
                        ),
                    ], spacing=15),
                    padding=20,
                ),
            ], spacing=0, expand=True),
            expand=True,
        )

    def show_main_app():
        """Show the main application interface."""
        page.controls.clear()

        # Create main layout - FIXED: Proper NavigationRail height handling
        main_content = None
        if current_view == "students":
            main_content = create_student_view()
        elif current_view == "enrol_face":
            main_content = create_enrol_face_view()
        elif current_view == "live_attendance":
            main_content = create_live_attendance_view()
        elif current_view == "attendance":
            main_content = create_attendance_view()
        elif current_view == "fees":
            main_content = create_fees_view()

        # FIXED: Use Column with expand instead of trying to set NavigationRail height
        page.add(
            create_app_bar(),
            ft.Row([
                create_navigation_rail(),
                ft.VerticalDivider(width=1),
                ft.Container(
                    content=main_content,
                    expand=True,
                ),
            ], expand=True)
        )
        page.update()
    
    def logout(e):
        """Logout current user."""
        nonlocal current_user
        current_user = None
        show_login()
    
    def show_login():
        """Show login screen."""
        page.controls.clear()
        
        # Use prefix_icon (works in 0.28.3 despite deprecation warning)
        username_field = ft.TextField(
            label="Username",
            prefix_icon=ft.Icons.PERSON,
            width=300,
            autofocus=True,
        )
        
        password_field = ft.TextField(
            label="Password",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            width=300,
        )
        
        def handle_login(e):
            nonlocal current_user
            if authenticate_user(username_field.value, password_field.value):
                current_user = username_field.value
                show_main_app()
            else:
                show_snackbar("Invalid username or password!", True)
        
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Image(
                        src="https://cdn-icons-png.flaticon.com/512/2966/2966307.png",
                        width=100,
                        height=100,
                    ),
                    ft.Text("School Management System", size=24, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=20),
                    username_field,
                    password_field,
                    ft.ElevatedButton(
                        "Login",
                        icon=ft.Icons.LOGIN,
                        width=300,
                        on_click=handle_login,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                alignment=ft.alignment.center,
                expand=True,
            )
        )
        page.update()
    
    # Initialize database and show login
    init_db()
    show_login()


if __name__ == "__main__":
    ft.app(target=main)
