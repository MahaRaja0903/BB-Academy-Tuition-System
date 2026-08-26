
import frappe
from frappe.utils import getdate, add_days, get_first_day, get_last_day

def execute(filters=None):
    columns = [
        {"fieldname": "student", "label": "Student ID", "fieldtype": "Link", "options": "Student", "width": 120},
        {"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "standard", "label": "Standard", "fieldtype": "Link", "options": "Standard", "width": 100},
        {"fieldname": "batch", "label": "Batch", "fieldtype": "Link", "options": "Batch", "width": 100},
        {"fieldname": "attendance_date", "label": "Date", "fieldtype": "Date", "width": 100},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 100},
        {"fieldname": "modified_by", "label": "Marked By", "fieldtype": "Data", "width": 150}
    ]
    
    conditions = ""
    if filters.get("attendance_date"): conditions += " AND a.attendance_date = %(attendance_date)s"
    if filters.get("standard"): conditions += " AND a.standard = %(standard)s"
    if filters.get("batch"): conditions += " AND s.current_batch = %(batch)s"
    if filters.get("status") and filters.get("status") != "All":
        if filters.get("status") == "Pending":
            # Pending means active student with no attendance record
            return get_pending_students(columns, filters)
        else:
            conditions += " AND a.status = %(status)s"
            
    data = frappe.db.sql(f"""
        SELECT a.student, a.student_name, a.standard, s.current_batch as batch, a.attendance_date, a.status, a.modified_by
        FROM `tabStudent Attendance` a
        JOIN `tabStudent` s ON a.student = s.name
        WHERE a.docstatus < 2 {conditions}
        ORDER BY a.student ASC
    """, filters, as_dict=True)
    
    return columns, data

def get_pending_students(columns, filters):
    date = filters.get("attendance_date")
    std = filters.get("standard")
    batch = filters.get("batch")
    
    std_cond = f" AND standard = '{std}'" if std else ""
    batch_cond = f" AND current_batch = '{batch}'" if batch else ""
    
    data = frappe.db.sql(f"""
        SELECT name as student, student_name, standard, current_batch as batch, %s as attendance_date, 'Pending' as status
        FROM `tabStudent`
        WHERE status = 'Active' AND admission_date <= %s {std_cond} {batch_cond}
        AND name NOT IN (
            SELECT student FROM `tabStudent Attendance` WHERE attendance_date = %s
        )
    """, (date, date, date), as_dict=True)
    return columns, data
