import sqlite3
from datetime import datetime, date, timedelta
from typing import List, Optional, cast
import sys
import os
sys.path.append(os.path.dirname(__file__))
from models import Student, Batch, Class, AttendanceRecord, FeeRecord, FeeTemplate

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
            name TEXT NOT NULL UNIQUE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            start_time TEXT,
            end_time TEXT,
            start_date DATE,
            end_date DATE,
            recurrence_pattern INTEGER DEFAULT 127
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fee_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            amount REAL NOT NULL,
            frequency TEXT CHECK(frequency IN ('One-time', 'Monthly', 'Annual')),
            batch_id INTEGER,
            is_active BOOLEAN DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES batches (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fee_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            generated_fee_id INTEGER,
            applied_date TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT CHECK(status IN ('Applied', 'Generated', 'Canceled')),
            FOREIGN KEY (template_id) REFERENCES fee_templates (id),
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (generated_fee_id) REFERENCES fees (id),
            UNIQUE(template_id, student_id, applied_date)
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

    # Migration: Add start_time and end_time columns to classes table if they don't exist
    try:
        cursor.execute("ALTER TABLE classes ADD COLUMN start_time TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE classes ADD COLUMN end_time TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Migration: Add new scheduling columns to classes table if they don't exist
    try:
        cursor.execute("ALTER TABLE classes ADD COLUMN start_date DATE")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE classes ADD COLUMN end_date DATE")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE classes ADD COLUMN recurrence_pattern INTEGER DEFAULT 127")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Migration: Remove old time columns from batches table if they exist (migration to class-based)
    try:
        cursor.execute("ALTER TABLE batches DROP COLUMN start_time")
    except sqlite3.OperationalError:
        pass  # Column doesn't exist
    try:
        cursor.execute("ALTER TABLE batches DROP COLUMN end_time")
    except sqlite3.OperationalError:
        pass  # Column doesn't exist

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
    cursor.execute("SELECT id, name FROM batches ORDER BY name")
    batches = [Batch(row['id'], row['name'], "", "") for row in cursor.fetchall()]
    conn.close()
    return batches


def add_batch(name: str, start_time: str = "", end_time: str = "") -> bool:
    """Add a new batch to database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO batches (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def get_all_classes() -> List[Class]:
    """Retrieve all classes from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, start_time, end_time, start_date, end_date, recurrence_pattern FROM classes ORDER BY name")
    classes = [Class(row['id'], row['name'], row['start_time'] or "", row['end_time'] or "", row['recurrence_pattern'] or 127, row['start_date'], row['end_date']) for row in cursor.fetchall()]
    conn.close()
    return classes


def add_class(name: str, start_time: str = "", end_time: str = "", start_date: Optional[str] = None, end_date: Optional[str] = None, recurrence_pattern: int = 127) -> bool:
    """Add a new class to database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO classes (name, start_time, end_time, start_date, end_date, recurrence_pattern) VALUES (?, ?, ?, ?, ?, ?)", (name, start_time, end_time, start_date, end_date, recurrence_pattern))
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


def get_all_fee_templates() -> List[FeeTemplate]:
    """Retrieve all fee templates."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ft.id, ft.name, ft.description, ft.amount, ft.frequency,
               ft.batch_id, b.name as batch_name, ft.is_active, ft.created_at
        FROM fee_templates ft
        LEFT JOIN batches b ON ft.batch_id = b.id
        ORDER BY ft.name
    """)
    templates = []
    for row in cursor.fetchall():
        template = FeeTemplate(
            row['id'],
            row['name'],
            row['description'] or "",
            row['amount'],
            row['frequency'],
            row['batch_id'],
            row['batch_name'] or "All Batches",
            bool(row['is_active']),
            row['created_at'] or ""
        )
        templates.append(template)
    conn.close()
    return templates


def add_fee_template(name: str, description: str, amount: float, frequency: str,
                    batch_id: Optional[int] = None) -> bool:
    """Add a new fee template."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fee_templates (name, description, amount, frequency, batch_id)
            VALUES (?, ?, ?, ?, ?)
        """, (name, description, amount, frequency, batch_id))
        template_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Auto-apply to existing students if batch-specific
        if batch_id:
            apply_template_to_batch_students(cast(int, template_id), batch_id)
        else:
            apply_template_to_all_students(cast(Optional[int], template_id))

        return True
    except sqlite3.IntegrityError:
        return False


def update_fee_template(template_id: int, name: str, description: str, amount: float,
                       frequency: str, batch_id: Optional[int] = None, is_active: bool = True) -> bool:
    """Update an existing fee template."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE fee_templates
            SET name = ?, description = ?, amount = ?, frequency = ?,
                batch_id = ?, is_active = ?
            WHERE id = ?
        """, (name, description, amount, frequency, batch_id, is_active, template_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def delete_fee_template(template_id: int) -> bool:
    """Delete a fee template and all its applications."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Delete all generated fees from this template
        cursor.execute("""
            DELETE FROM fees WHERE id IN (
                SELECT generated_fee_id FROM fee_applications
                WHERE template_id = ? AND generated_fee_id IS NOT NULL
            )
        """, (template_id,))
        # Delete all applications
        cursor.execute("DELETE FROM fee_applications WHERE template_id = ?", (template_id,))
        # Delete template
        cursor.execute("DELETE FROM fee_templates WHERE id = ?", (template_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def apply_template_to_batch_students(template_id: int, batch_id: Optional[int]) -> bool:
    """Apply a fee template to all students in a specific batch."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get template details
        cursor.execute("SELECT * FROM fee_templates WHERE id = ?", (template_id,))
        template = cursor.fetchone()
        if not template:
            return False

        # Get all students in the batch
        cursor.execute("""
            SELECT id, name FROM students WHERE batch_id = ?
        """, (batch_id,))
        students = cursor.fetchall()

        # Apply template to each student
        for student in students:
            cursor.execute("""
                INSERT INTO fee_applications (template_id, student_id, status)
                VALUES (?, ?, 'Applied')
                ON CONFLICT(template_id, student_id, applied_date) DO NOTHING
            """, (template_id, student['id']))

            # For one-time fees, generate immediately
            if template['frequency'] == 'One-time':
                # Generate due date (today)
                due_date = date.today().isoformat()
                cursor.execute("""
                    INSERT INTO fees (student_id, amount, due_date, status, description)
                    VALUES (?, ?, ?, 'Pending', ?)
                """, (student['id'], template['amount'], due_date, template['name']))

                # Link the generated fee
                generated_fee_id = cursor.lastrowid
                cursor.execute("""
                    UPDATE fee_applications
                    SET generated_fee_id = ?, status = 'Generated'
                    WHERE template_id = ? AND student_id = ?
                """, (generated_fee_id, template_id, student['id']))

        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def apply_template_to_all_students(template_id: Optional[int]) -> bool:
    """Apply a fee template to all students."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get template details
        cursor.execute("SELECT * FROM fee_templates WHERE id = ?", (template_id,))
        template = cursor.fetchone()
        if not template:
            return False

        # Get all students
        cursor.execute("SELECT id, name FROM students")
        students = cursor.fetchall()

        # Apply template to each student
        for student in students:
            cursor.execute("""
                INSERT INTO fee_applications (template_id, student_id, status)
                VALUES (?, ?, 'Applied')
                ON CONFLICT(template_id, student_id, applied_date) DO NOTHING
            """, (template_id, student['id']))

            # For one-time fees, generate immediately
            if template['frequency'] == 'One-time':
                # Generate due date (today)
                due_date = date.today().isoformat()
                cursor.execute("""
                    INSERT INTO fees (student_id, amount, due_date, status, description)
                    VALUES (?, ?, ?, 'Pending', ?)
                """, (student['id'], template['amount'], due_date, template['name']))

                # Link the generated fee
                generated_fee_id = cursor.lastrowid
                cursor.execute("""
                    UPDATE fee_applications
                    SET generated_fee_id = ?, status = 'Generated'
                    WHERE template_id = ? AND student_id = ?
                """, (generated_fee_id, template_id, student['id']))

        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def generate_monthly_fees() -> bool:
    """Generate monthly fees for all active monthly templates."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get current date for this month
        current_date = date.today()
        due_date = current_date.replace(day=1).isoformat()  # 1st of current month

        # Get all active monthly templates
        cursor.execute("""
            SELECT * FROM fee_templates
            WHERE frequency = 'Monthly' AND is_active = 1
        """)
        templates = cursor.fetchall()

        for template in templates:
            # Get students for this template
            if template['batch_id']:
                # Batch-specific
                cursor.execute("""
                    SELECT s.id, s.name FROM students s
                    JOIN fee_applications fa ON s.id = fa.student_id
                    WHERE s.batch_id = ? AND fa.template_id = ? AND fa.status = 'Applied'
                """, (template['batch_id'], template['id']))
            else:
                # All students
                cursor.execute("""
                    SELECT s.id, s.name FROM students s
                    JOIN fee_applications fa ON s.id = fa.student_id
                    WHERE fa.template_id = ? AND fa.status = 'Applied'
                """, (template['id'],))

            students = cursor.fetchall()

            for student in students:
                # Check if fee already exists for this month
                cursor.execute("""
                    SELECT COUNT(*) FROM fees
                    WHERE student_id = ? AND description = ? AND due_date LIKE ?
                """, (student['id'], template['name'], f"{current_date.year}-{current_date.month:02d}%"))

                if cursor.fetchone()[0] == 0:
                    # Generate the fee
                    cursor.execute("""
                        INSERT INTO fees (student_id, amount, due_date, status, description)
                        VALUES (?, ?, ?, 'Pending', ?)
                    """, (student['id'], template['amount'], due_date, f"{template['name']} - {current_date.strftime('%B %Y')}"))

        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def generate_annual_fees() -> bool:
    """Generate annual fees for all active annual templates."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get current date
        current_date = date.today()
        due_date = current_date.replace(month=1, day=1).isoformat()  # January 1st

        # Get all active annual templates
        cursor.execute("""
            SELECT * FROM fee_templates
            WHERE frequency = 'Annual' AND is_active = 1
        """)
        templates = cursor.fetchall()

        for template in templates:
            # Get students for this template
            if template['batch_id']:
                # Batch-specific
                cursor.execute("""
                    SELECT s.id, s.name FROM students s
                    JOIN fee_applications fa ON s.id = fa.student_id
                    WHERE s.batch_id = ? AND fa.template_id = ? AND fa.status = 'Applied'
                """, (template['batch_id'], template['id']))
            else:
                # All students
                cursor.execute("""
                    SELECT s.id, s.name FROM students s
                    JOIN fee_applications fa ON s.id = fa.student_id
                    WHERE fa.template_id = ? AND fa.status = 'Applied'
                """, (template['id'],))

            students = cursor.fetchall()

            for student in students:
                # Check if fee already exists for this year
                cursor.execute("""
                    SELECT COUNT(*) FROM fees
                    WHERE student_id = ? AND description = ? AND due_date LIKE ?
                """, (student['id'], template['name'], f"{current_date.year}%"))

                if cursor.fetchone()[0] == 0:
                    # Generate the fee
                    cursor.execute("""
                        INSERT INTO fees (student_id, amount, due_date, status, description)
                        VALUES (?, ?, ?, 'Pending', ?)
                    """, (student['id'], template['amount'], due_date, f"{template['name']} - {current_date.year}"))

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
        SELECT b.id, b.name
        FROM batches b
        JOIN students s ON s.batch_id = b.id
        WHERE s.id = ?
    """, (student_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return Batch(row['id'], row['name'], "", "")
    return None


def get_current_attendance_status(student_id: int) -> str:
    """Determine attendance status based on current time and class schedule."""
    from datetime import datetime, time, timedelta
    # Get student's class with scheduling constraints
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.start_time, c.end_time, c.start_date, c.end_date, c.recurrence_pattern
        FROM classes c
        JOIN students s ON s.class_id = c.id
        WHERE s.id = ?
    """, (student_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row['start_time'] or not row['end_time']:
        return "Present"  # Default if no class times set

    current_date = date.today()

    # Check date range constraints - return "Present" if outside range
    if row['start_date'] and row['end_date']:
        try:
            start_date = date.fromisoformat(row['start_date'])
            end_date = date.fromisoformat(row['end_date'])
            if current_date < start_date or current_date > end_date:
                return "Present"
        except ValueError:
            pass  # Invalid dates, continue with time logic

    # Check day recurrence pattern - return "Present" if class doesn't run today
    recurrence_pattern = row['recurrence_pattern'] or 127  # Default to all days if null
    weekday = current_date.weekday()  # 0=Monday, 6=Sunday
    if (recurrence_pattern & (1 << weekday)) == 0:
        return "Present"

    # Existing time-based logic
    try:
        # Parse class times
        start_time = datetime.strptime(row['start_time'], "%H:%M").time()
        end_time = datetime.strptime(row['end_time'], "%H:%M").time()
        current_time = datetime.now().time()

        # Calculate late threshold (15 minutes after start time)
        late_threshold = datetime.combine(date.today(), start_time) + timedelta(minutes=15)
        late_threshold_time = late_threshold.time()

        if current_time <= start_time:
            return "Present"  # On time or before start
        elif current_time <= late_threshold_time:
            return "Late"  # Late but within grace period (15 mins)
        elif current_time <= end_time:
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
