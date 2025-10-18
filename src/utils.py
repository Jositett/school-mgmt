import csv
from datetime import datetime
from .database import get_all_students


def export_students_to_csv():
    """Export all students to CSV file."""
    students = get_all_students()
    filename = f"students_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'Name', 'Age', 'Batch', 'Class'])
        for student in students:
            writer.writerow([student.id, student.name, student.age,
                           student.batch_name, student.class_name])
    return filename
