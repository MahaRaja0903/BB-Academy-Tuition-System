
import frappe
from frappe.utils import getdate, add_days, get_first_day, get_last_day

def execute(filters=None):
    columns = [
        {"fieldname": "attendance_date", "label": "Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "day", "label": "Day", "fieldtype": "Data", "width": 120},
        {"fieldname": "standard", "label": "Standard", "fieldtype": "Data", "width": 100},
        {"fieldname": "batch", "label": "Batch", "fieldtype": "Data", "width": 100},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 100}
    ]
    
    data = frappe.db.sql("""
        SELECT attendance_date, DAYNAME(attendance_date) as day, standard, batch, status
        FROM `tabStudent Attendance`
        WHERE student = %(student)s AND attendance_date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY attendance_date ASC
    """, filters, as_dict=True)
    
    # Calculate summary
    w = p = a = l = 0
    for r in data:
        w += 1
        if r.status == 'Present': p += 1
        elif r.status == 'Absent': a += 1
        elif r.status == 'Late': l += 1
    
    pct = round(((p+l)/w)*100, 2) if w > 0 else 0
    
    report_summary = [
        {"value": w, "indicator": "Blue", "label": "Working Days", "datatype": "Int"},
        {"value": p, "indicator": "Green", "label": "Present", "datatype": "Int"},
        {"value": a, "indicator": "Red", "label": "Absent", "datatype": "Int"},
        {"value": l, "indicator": "Orange", "label": "Late", "datatype": "Int"},
        {"value": f"{pct}%", "indicator": "Green" if pct >= 75 else "Red", "label": "Attendance %", "datatype": "Data"}
    ]
    
    return columns, data, None, None, report_summary
