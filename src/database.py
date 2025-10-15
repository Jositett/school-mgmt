import sqlite3
from datetime import datetime, date
from typing import List, Optional
from models import Student, Batch, Class, AttendanceRecord, FeeRecord

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
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            start_time TEXT,
            end_time TEXT
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
            batch_id INTEGER,
            class_id INTEGER,
            FOREIGN KEY (batch_id) REFERENCES batches (id),
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


# Database operations
def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_batches() -> List[Batch]:
    """Retrieve all batches from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, start_time, end_time FROM batches ORDER BY name")
    batches = [Batch(row['id'], row['name'], row['start_time'] or "", row['end_time'] or "") for row in cursor.fetchall()]
    conn.close()
    return batches


def add_batch(name: str, start_time: str = "09:00", end_time: str = "17:00") -> bool:
    """Add a new batch to database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO batches (name, start_time, end_time) VALUES (?, ?, ?)", (name, start_time, end_time))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


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
            SELECT s.id, s.name, s.age, s.batch_id, b.name as batch_name,
                   s.class_id, c.name as class_name
            FROM students s
            LEFT JOIN batches b ON s.batch_id = b.id
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.name LIKE ? OR b.name LIKE ? OR c.name LIKE ?
            ORDER BY s.name
        """
        search_term = f"%{search_query}%"
        cursor.execute(query, (search_term, search_term, search_term))
    else:
        query = """
            SELECT s.id, s.name, s.age, s.batch_id, b.name as batch_name,
                   s.class_id, c.name as class_name
            FROM students s
            LEFT JOIN batches b ON s.batch_id = b.id
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
            row['batch_id'],
            row['batch_name'] or "",
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
        SELECT s.id, s.name, s.age, s.batch_id, b.name as batch_name,
               s.class_id, c.name as class_name
        FROM students s
        LEFT JOIN batches b ON s.batch_id = b.id
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
            row['batch_id'],
            row['batch_name'] or "",
            row['class_id'],
            row['class_name'] or ""
        )
    return None


def add_student(name: str, age: int, batch_id: Optional[int] = None, class_id: Optional[int] = None) -> bool:
    """Add a new student to database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (name, age, batch_id, class_id) VALUES (?, ?, ?, ?)",
            (name, age, batch_id, class_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def update_student(student_id: int, name: str, age: int,
                   batch_id: Optional[int] = None, class_id: Optional[int] = None) -> bool:
    """Update an existing student."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE students SET name = ?, age = ?, batch_id = ?, class_id = ? WHERE id = ?",
            (name, age, batch_id, class_id, student_id)
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


def export_students_to_csv():
    """Export all students to CSV file."""
    import csv
    students = get_all_students()
    filename = f"students_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'Name', 'Age', 'Batch', 'Class'])
        for student in students:
            writer.writerow([student.id, student.name, student.age,
                           student.batch_name, student.class_name])
    return filename


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


def get_student_batch(student_id: int) -> Optional[Batch]:
    """Get batch information for a specific student."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.id, b.name, b.start_time, b.end_time
        FROM batches b
        JOIN students s ON s.batch_id = b.id
        WHERE s.id = ?
    """, (student_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return Batch(row['id'], row['name'], row['start_time'] or "", row['end_time'] or "")
    return None


def get_current_attendance_status(student_id: int) -> str:
    """Determine attendance status based on current time and batch schedule."""
    from datetime import datetime, time
    batch = get_student_batch(student_id)
    if not batch or not batch.start_time or not batch.end_time:
        return "Present"  # Default if no batch times set

    try:
        # Parse batch times
        start_time = datetime.strptime(batch.start_time, "%H:%M").time()
        end_time = datetime.strptime(batch.end_time, "%H:%M").time()
        current_time = datetime.now().time()

        # Calculate late threshold (30 minutes after start time)
        from datetime import timedelta
        late_threshold = datetime.combine(datetime.today(), start_time) + timedelta(minutes=30)
        late_threshold_time = late_threshold.time()

        if current_time <= start_time:
            return "Present"  # On time or before start
        elif start_time < current_time <= late_threshold_time:
            return "Late"  # Late but within grace period (30 mins)
        elif late_threshold_time < current_time <= end_time:
            return "Late"  # Still late if within session time
        else:
            return "Absent"  # After session end time
    except ValueError:
        return "Present"  # Default on parsing errors


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user credentials."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?",
                  (username, password))
    result = cursor.fetchone()
    conn.close()
    return result is not None


class FaceService:
    """Singleton that keeps one in-memory copy of all encodings."""
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_encodings()
        return cls._instance

    # ---------- public API ----------
    def enrol_student(self, student_id: int, images_or_video: list) -> bool:
        """Pass either a list of cv2 images or a list with one video frame every 200 ms."""
        if not FACE_RECOGNITION_AVAILABLE:
            return False
        import cv2
        import numpy as np
        encodings = []
        for frame in images_or_video:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes = face_recognition.face_locations(rgb, model="hog")  # type: ignore # or "cnn" if GPU
            if boxes:
                encodings.append(face_recognition.face_encodings(rgb, boxes)[0])  # type: ignore
        if len(encodings) < 1:
            return False
        mean_encoding = np.mean(encodings, axis=0)                   # simple average
        self._save_encoding(student_id, mean_encoding)
        self._load_encodings()                                       # refresh RAM
        return True

    def recognise(self, frame) -> list[tuple[int, float]]:
        """Return [(student_id, distance), …] for all faces in frame (distance ≤ 0.45)."""
        if not FACE_RECOGNITION_AVAILABLE:
            return []
        import cv2
        import numpy as np
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(rgb, model="hog")  # type: ignore
        if not boxes:
            return []
        unknown_encodings = face_recognition.face_encodings(rgb, boxes)  # type: ignore
        results = []
        for enc in unknown_encodings:
            distances = face_recognition.face_distance(self.known_encodings, enc)  # type: ignore
            best_idx = np.argmin(distances)
            if distances[best_idx] <= 0.45:          # tune threshold if needed
                results.append((self.known_ids[best_idx], float(distances[best_idx])))
        return results

    # ---------- internal ----------
    def _load_encodings(self):
        import numpy as np
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT student_id, encoding FROM face_encodings").fetchall()
        conn.close()
        self.known_ids = [r[0] for r in rows]
        self.known_encodings = [np.frombuffer(r[1], dtype=np.float32) for r in rows]

    def _save_encoding(self, student_id: int, enc):
        import numpy as np
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO face_encodings(student_id, encoding, updated_at) VALUES (?,?,?)",
            (student_id, enc.tobytes(), datetime.now().isoformat()))
        conn.commit()
        conn.close()
