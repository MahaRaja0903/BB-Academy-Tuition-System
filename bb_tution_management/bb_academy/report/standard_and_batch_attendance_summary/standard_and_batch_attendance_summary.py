import frappe
from frappe.utils import getdate, add_days, get_first_day, get_last_day

def execute(filters=None):
    columns = [
        {"fieldname": "standard", "label": "Standard", "fieldtype": "Link", "options": "Standard", "width": 120},
        {"fieldname": "batch", "label": "Batch", "fieldtype": "Link", "options": "Batch", "width": 120},
        {"fieldname": "total_students", "label": "Total Students", "fieldtype": "Int", "width": 120},
        {"fieldname": "working_days", "label": "Working Days (Total records)", "fieldtype": "Int", "width": 150},
        {"fieldname": "present", "label": "Present", "fieldtype": "Int", "width": 100},
        {"fieldname": "absent", "label": "Absent", "fieldtype": "Int", "width": 100},
        {"fieldname": "late", "label": "Late", "fieldtype": "Int", "width": 100},
        {"fieldname": "attendance_pct", "label": "Attendance %", "fieldtype": "Data", "width": 120}
    ]
    
    data = frappe.db.sql("""
        SELECT a.standard, s.current_batch as batch, 
               COUNT(DISTINCT a.student) as total_students,
               COUNT(a.name) as working_days,
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present,
               SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) as absent,
               SUM(CASE WHEN a.status='Late' THEN 1 ELSE 0 END) as late
        FROM `tabStudent Attendance` a
        JOIN `tabStudent` s ON a.student = s.name
        WHERE a.attendance_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY a.standard, s.current_batch
    """, filters, as_dict=True)
    
    for r in data:
        w = r.working_days
        att = r.present + r.late
        r.attendance_pct = f"{round((att/w)*100, 2)}%" if w > 0 else "0%"
        
    return columns, data
