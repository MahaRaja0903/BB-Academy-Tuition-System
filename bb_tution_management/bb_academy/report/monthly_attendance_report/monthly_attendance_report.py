
import frappe
from frappe.utils import getdate, add_days, get_first_day, get_last_day

def execute(filters=None):
    columns = [
        {"fieldname": "student", "label": "Student ID", "fieldtype": "Link", "options": "Student", "width": 120},
        {"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "standard", "label": "Standard", "fieldtype": "Data", "width": 100},
        {"fieldname": "batch", "label": "Batch", "fieldtype": "Data", "width": 100},
        {"fieldname": "working_days", "label": "Working Days", "fieldtype": "Int", "width": 100},
        {"fieldname": "present", "label": "Present", "fieldtype": "Int", "width": 100},
        {"fieldname": "absent", "label": "Absent", "fieldtype": "Int", "width": 100},
        {"fieldname": "late", "label": "Late", "fieldtype": "Int", "width": 100},
        {"fieldname": "attendance_pct", "label": "Attendance %", "fieldtype": "Data", "width": 100}
    ]
    
    # We will compute month start/end based on a Month filter. Since frappe doesn't have a Month field easily, we'll use from/to date.
    data = frappe.db.sql("""
        SELECT 
            a.student, a.student_name, a.standard, s.current_batch as batch,
            COUNT(a.name) as working_days,
            SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present,
            SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) as absent,
            SUM(CASE WHEN a.status='Late' THEN 1 ELSE 0 END) as late
        FROM `tabStudent Attendance` a
        JOIN `tabStudent` s ON a.student = s.name
        WHERE a.attendance_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY a.student, a.student_name, a.standard, s.current_batch
    """, filters, as_dict=True)
    
    for r in data:
        w = r.working_days
        att = r.present + r.late
        r.attendance_pct = f"{round((att/w)*100, 2)}%" if w > 0 else "0%"
        
    return columns, data
