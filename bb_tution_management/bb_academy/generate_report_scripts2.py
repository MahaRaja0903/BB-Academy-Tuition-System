import os

base_path = "/home/frappe/dreamtech-bench/apps/bb_tution_management/bb_tution_management/bb_academy/report"
common_imports = "import frappe\nfrom frappe.utils import getdate, add_days, get_first_day, get_last_day\n"

# 4. Standard and Batch Attendance Summary
sb_py = common_imports + """
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
    
    data = frappe.db.sql(\"\"\"
        SELECT standard, batch, 
               COUNT(DISTINCT student) as total_students,
               COUNT(name) as working_days,
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present,
               SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) as absent,
               SUM(CASE WHEN status='Late' THEN 1 ELSE 0 END) as late
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY standard, batch
    \"\"\", filters, as_dict=True)
    
    for r in data:
        w = r.working_days
        att = r.present + r.late
        r.attendance_pct = f"{round((att/w)*100, 2)}%" if w > 0 else "0%"
        
    return columns, data
"""
sb_js = """
frappe.query_reports["Standard and Batch Attendance Summary"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.month_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.month_end(), "reqd": 1}
    ]
};
"""
with open(os.path.join(base_path, "standard_and_batch_attendance_summary/standard_and_batch_attendance_summary.py"), "w") as f: f.write(sb_py)
with open(os.path.join(base_path, "standard_and_batch_attendance_summary/standard_and_batch_attendance_summary.js"), "w") as f: f.write(sb_js)

# 5. Absent Student Report
abs_py = common_imports + """
def execute(filters=None):
    columns = [
        {"fieldname": "student", "label": "Student ID", "fieldtype": "Link", "options": "Student", "width": 120},
        {"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "standard", "label": "Standard", "fieldtype": "Data", "width": 100},
        {"fieldname": "batch", "label": "Batch", "fieldtype": "Data", "width": 100},
        {"fieldname": "absent_days", "label": "Absent Days", "fieldtype": "Int", "width": 100},
        {"fieldname": "working_days", "label": "Working Days", "fieldtype": "Int", "width": 100},
        {"fieldname": "attendance_pct", "label": "Attendance %", "fieldtype": "Data", "width": 100}
    ]
    
    min_absent = filters.get("min_absent") or 1
    
    data = frappe.db.sql(\"\"\"
        SELECT student, student_name, standard, batch,
               SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) as absent_days,
               COUNT(name) as working_days,
               SUM(CASE WHEN status IN ('Present', 'Late') THEN 1 ELSE 0 END) as att_days
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY student, student_name, standard, batch
        HAVING absent_days >= %(min_absent)s
        ORDER BY absent_days DESC
    \"\"\", {"from_date": filters.get("from_date"), "to_date": filters.get("to_date"), "min_absent": min_absent}, as_dict=True)
    
    for r in data:
        w = r.working_days
        r.attendance_pct = f"{round((r.att_days/w)*100, 2)}%" if w > 0 else "0%"
        
    return columns, data
"""
abs_js = """
frappe.query_reports["Absent Student Report"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.month_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.month_end(), "reqd": 1},
        {"fieldname":"min_absent", "label":"Minimum Absent Days", "fieldtype":"Int", "default": 1}
    ]
};
"""
with open(os.path.join(base_path, "absent_student_report/absent_student_report.py"), "w") as f: f.write(abs_py)
with open(os.path.join(base_path, "absent_student_report/absent_student_report.js"), "w") as f: f.write(abs_js)


# 6. Late Entry Report
late_py = common_imports + """
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
    
    data = frappe.db.sql(\"\"\"
        SELECT student, student_name, standard, batch,
               SUM(CASE WHEN status='Late' THEN 1 ELSE 0 END) as late_days,
               COUNT(name) as working_days,
               SUM(CASE WHEN status IN ('Present', 'Late') THEN 1 ELSE 0 END) as att_days
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY student, student_name, standard, batch
        HAVING late_days >= %(min_late)s
        ORDER BY late_days DESC
    \"\"\", {"from_date": filters.get("from_date"), "to_date": filters.get("to_date"), "min_late": min_late}, as_dict=True)
    
    for r in data:
        w = r.working_days
        r.attendance_pct = f"{round((r.att_days/w)*100, 2)}%" if w > 0 else "0%"
        
    return columns, data
"""
late_js = """
frappe.query_reports["Late Entry Report"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.month_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.month_end(), "reqd": 1},
        {"fieldname":"min_late", "label":"Minimum Late Entries", "fieldtype":"Int", "default": 1}
    ]
};
"""
with open(os.path.join(base_path, "late_entry_report/late_entry_report.py"), "w") as f: f.write(late_py)
with open(os.path.join(base_path, "late_entry_report/late_entry_report.js"), "w") as f: f.write(late_js)

