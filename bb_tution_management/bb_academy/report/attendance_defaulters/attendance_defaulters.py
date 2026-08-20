import frappe
from frappe.utils import getdate, add_days, get_first_day, get_last_day

def execute(filters=None):
    columns = [
        {"fieldname": "student", "label": "Student ID", "fieldtype": "Link", "options": "Student", "width": 120},
        {"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "standard", "label": "Standard", "fieldtype": "Data", "width": 100},
        {"fieldname": "batch", "label": "Batch", "fieldtype": "Data", "width": 100},
        {"fieldname": "present", "label": "Present", "fieldtype": "Int", "width": 100},
        {"fieldname": "absent", "label": "Absent", "fieldtype": "Int", "width": 100},
        {"fieldname": "late", "label": "Late", "fieldtype": "Int", "width": 100},
        {"fieldname": "attendance_pct", "label": "Attendance %", "fieldtype": "Data", "width": 120}
    ]
    
    threshold = filters.get("threshold") or 75
    
    data = frappe.db.sql("""
        SELECT student, student_name, standard, batch,
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present,
               SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) as absent,
               SUM(CASE WHEN status='Late' THEN 1 ELSE 0 END) as late,
               COUNT(name) as working_days
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY student, student_name, standard, batch
    """, filters, as_dict=True)
    
    out = []
    for r in data:
        w = r.working_days
        att = r.present + r.late
        pct = (att/w)*100 if w > 0 else 0
        if pct < threshold:
            r.attendance_pct = f"{round(pct, 2)}%"
            out.append(r)
            
    out.sort(key=lambda x: (x.present+x.late)/x.working_days)
    return columns, out
