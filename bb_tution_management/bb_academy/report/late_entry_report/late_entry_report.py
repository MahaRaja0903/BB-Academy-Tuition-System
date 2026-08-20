import frappe
from frappe.utils import getdate, add_days, get_first_day, get_last_day

def execute(filters=None):
    columns = [
        {"fieldname": "student", "label": "Student ID", "fieldtype": "Link", "options": "Student", "width": 120},
        {"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "standard", "label": "Standard", "fieldtype": "Data", "width": 100},
        {"fieldname": "batch", "label": "Batch", "fieldtype": "Data", "width": 100},
        {"fieldname": "late_days", "label": "Late Entries", "fieldtype": "Int", "width": 100},
        {"fieldname": "working_days", "label": "Working Days", "fieldtype": "Int", "width": 100},
        {"fieldname": "attendance_pct", "label": "Attendance %", "fieldtype": "Data", "width": 100}
    ]
    
    min_late = filters.get("min_late") or 1
    
    data = frappe.db.sql("""
        SELECT student, student_name, standard, batch,
               SUM(CASE WHEN status='Late' THEN 1 ELSE 0 END) as late_days,
               COUNT(name) as working_days,
               SUM(CASE WHEN status IN ('Present', 'Late') THEN 1 ELSE 0 END) as att_days
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY student, student_name, standard, batch
        HAVING late_days >= %(min_late)s
        ORDER BY late_days DESC
    """, {"from_date": filters.get("from_date"), "to_date": filters.get("to_date"), "min_late": min_late}, as_dict=True)
    
    for r in data:
        w = r.working_days
        r.attendance_pct = f"{round((r.att_days/w)*100, 2)}%" if w > 0 else "0%"
        
    return columns, data
