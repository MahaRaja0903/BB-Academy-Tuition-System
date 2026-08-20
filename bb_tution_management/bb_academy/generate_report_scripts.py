import os

base_path = "/home/frappe/dreamtech-bench/apps/bb_tution_management/bb_tution_management/bb_academy/report"

# Common helper logic for python reports
common_imports = """
import frappe
from frappe.utils import getdate, add_days, get_first_day, get_last_day
"""

# 1. Daily Attendance Report
daily_py = common_imports + """
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
    if filters.get("attendance_date"): conditions += " AND attendance_date = %(attendance_date)s"
    if filters.get("standard"): conditions += " AND standard = %(standard)s"
    if filters.get("batch"): conditions += " AND batch = %(batch)s"
    if filters.get("status") and filters.get("status") != "All":
        if filters.get("status") == "Pending":
            # Pending means active student with no attendance record
            return get_pending_students(columns, filters)
        else:
            conditions += " AND status = %(status)s"
            
    data = frappe.db.sql(f\"\"\"
        SELECT student, student_name, standard, batch, attendance_date, status, modified_by
        FROM `tabStudent Attendance`
        WHERE docstatus < 2 {conditions}
        ORDER BY student ASC
    \"\"\", filters, as_dict=True)
    
    return columns, data

def get_pending_students(columns, filters):
    date = filters.get("attendance_date")
    std = filters.get("standard")
    batch = filters.get("batch")
    
    std_cond = f" AND standard = '{std}'" if std else ""
    batch_cond = f" AND current_batch = '{batch}'" if batch else ""
    
    data = frappe.db.sql(f\"\"\"
        SELECT name as student, student_name, standard, current_batch as batch, %s as attendance_date, 'Pending' as status
        FROM `tabStudent`
        WHERE status = 'Active' AND admission_date <= %s {std_cond} {batch_cond}
        AND name NOT IN (
            SELECT student FROM `tabStudent Attendance` WHERE attendance_date = %s
        )
    \"\"\", (date, date, date), as_dict=True)
    return columns, data
"""
daily_js = """
frappe.query_reports["Daily Attendance Report"] = {
    "filters": [
        {"fieldname":"attendance_date", "label":"Date", "fieldtype":"Date", "default": frappe.datetime.get_today(), "reqd": 1},
        {"fieldname":"standard", "label":"Standard", "fieldtype":"Link", "options":"Standard"},
        {"fieldname":"batch", "label":"Batch", "fieldtype":"Link", "options":"Batch"},
        {"fieldname":"status", "label":"Status", "fieldtype":"Select", "options":"All\\nPresent\\nAbsent\\nLate\\nPending", "default": "All"}
    ]
};
"""

with open(os.path.join(base_path, "daily_attendance_report/daily_attendance_report.py"), "w") as f: f.write(daily_py)
with open(os.path.join(base_path, "daily_attendance_report/daily_attendance_report.js"), "w") as f: f.write(daily_js)

# 2. Student Attendance History
hist_py = common_imports + """
def execute(filters=None):
    columns = [
        {"fieldname": "attendance_date", "label": "Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "day", "label": "Day", "fieldtype": "Data", "width": 120},
        {"fieldname": "standard", "label": "Standard", "fieldtype": "Data", "width": 100},
        {"fieldname": "batch", "label": "Batch", "fieldtype": "Data", "width": 100},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 100}
    ]
    
    data = frappe.db.sql(\"\"\"
        SELECT attendance_date, DAYNAME(attendance_date) as day, standard, batch, status
        FROM `tabStudent Attendance`
        WHERE student = %(student)s AND attendance_date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY attendance_date ASC
    \"\"\", filters, as_dict=True)
    
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
"""
hist_js = """
frappe.query_reports["Student Attendance History"] = {
    "filters": [
        {"fieldname":"student", "label":"Student", "fieldtype":"Link", "options":"Student", "reqd": 1},
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.get_today(), "reqd": 1}
    ]
};
"""
with open(os.path.join(base_path, "student_attendance_history/student_attendance_history.py"), "w") as f: f.write(hist_py)
with open(os.path.join(base_path, "student_attendance_history/student_attendance_history.js"), "w") as f: f.write(hist_js)


# 3. Monthly Attendance Report
month_py = common_imports + """
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
    data = frappe.db.sql(\"\"\"
        SELECT 
            student, student_name, standard, batch,
            COUNT(name) as working_days,
            SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present,
            SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) as absent,
            SUM(CASE WHEN status='Late' THEN 1 ELSE 0 END) as late
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY student, student_name, standard, batch
    \"\"\", filters, as_dict=True)
    
    for r in data:
        w = r.working_days
        att = r.present + r.late
        r.attendance_pct = f"{round((att/w)*100, 2)}%" if w > 0 else "0%"
        
    return columns, data
"""
month_js = """
frappe.query_reports["Monthly Attendance Report"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.month_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.month_end(), "reqd": 1}
    ]
};
"""
with open(os.path.join(base_path, "monthly_attendance_report/monthly_attendance_report.py"), "w") as f: f.write(month_py)
with open(os.path.join(base_path, "monthly_attendance_report/monthly_attendance_report.js"), "w") as f: f.write(month_js)

