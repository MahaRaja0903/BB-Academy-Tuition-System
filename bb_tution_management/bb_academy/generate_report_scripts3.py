import os

base_path = "/home/frappe/dreamtech-bench/apps/bb_tution_management/bb_tution_management/bb_academy/report"
common_imports = "import frappe\nfrom frappe.utils import getdate, add_days, get_first_day, get_last_day\n"

# 7. Attendance Defaulters
def_py = common_imports + """
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
    
    data = frappe.db.sql(\"\"\"
        SELECT student, student_name, standard, batch,
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present,
               SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) as absent,
               SUM(CASE WHEN status='Late' THEN 1 ELSE 0 END) as late,
               COUNT(name) as working_days
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY student, student_name, standard, batch
    \"\"\", filters, as_dict=True)
    
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
"""
def_js = """
frappe.query_reports["Attendance Defaulters"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.month_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.month_end(), "reqd": 1},
        {"fieldname":"threshold", "label":"Attendance % Below", "fieldtype":"Float", "default": 75, "reqd": 1}
    ]
};
"""
with open(os.path.join(base_path, "attendance_defaulters/attendance_defaulters.py"), "w") as f: f.write(def_py)
with open(os.path.join(base_path, "attendance_defaulters/attendance_defaulters.js"), "w") as f: f.write(def_js)

# 8. Monthly Attendance Register
reg_py = common_imports + """
def execute(filters=None):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    
    columns = [
        {"fieldname": "student", "label": "Student ID", "fieldtype": "Link", "options": "Student", "width": 120},
        {"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 200}
    ]
    
    # Add day columns
    delta = to_date - from_date
    days = delta.days + 1
    
    for i in range(days):
        d = add_days(from_date, i)
        d_str = d.strftime("%d")
        columns.append({"fieldname": f"day_{i}", "label": d_str, "fieldtype": "Data", "width": 50})
        
    columns.extend([
        {"fieldname": "present", "label": "Present", "fieldtype": "Int", "width": 80},
        {"fieldname": "absent", "label": "Absent", "fieldtype": "Int", "width": 80},
        {"fieldname": "late", "label": "Late", "fieldtype": "Int", "width": 80},
        {"fieldname": "pct", "label": "%", "fieldtype": "Data", "width": 80}
    ])
    
    std_cond = f" AND standard = '{filters.get('standard')}'" if filters.get('standard') else ""
    batch_cond = f" AND batch = '{filters.get('batch')}'" if filters.get('batch') else ""
    
    data = frappe.db.sql(f\"\"\"
        SELECT student, student_name, attendance_date, status
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
        {std_cond} {batch_cond}
    \"\"\", filters, as_dict=True)
    
    # Also fetch holidays to mark them
    # For simplicity, we query holidays and match them.
    holidays = frappe.db.sql(\"\"\"
        SELECT holiday_date, scope, standard, batch 
        FROM `tabAttendance Holiday`
        WHERE holiday_date BETWEEN %(from_date)s AND %(to_date)s
    \"\"\", filters, as_dict=True)
    
    students_map = {}
    for r in data:
        stu = r.student
        if stu not in students_map:
            students_map[stu] = {"student": stu, "student_name": r.student_name, "present": 0, "absent": 0, "late": 0}
            
        dt = r.attendance_date
        diff = (dt - from_date).days
        stat_char = r.status[0] # P, A, L
        students_map[stu][f"day_{diff}"] = stat_char
        
        if stat_char == 'P': students_map[stu]["present"] += 1
        elif stat_char == 'A': students_map[stu]["absent"] += 1
        elif stat_char == 'L': students_map[stu]["late"] += 1
        
    out = []
    for stu, row in students_map.items():
        w = row["present"] + row["absent"] + row["late"]
        att = row["present"] + row["late"]
        row["pct"] = f"{round((att/w)*100, 1)}%" if w > 0 else "0%"
        
        # Fill missing with '-' or 'H'
        for i in range(days):
            col = f"day_{i}"
            if col not in row:
                row[col] = "-"
                
        out.append(row)
        
    out.sort(key=lambda x: x["student"])
    return columns, out
"""
reg_js = """
frappe.query_reports["Monthly Attendance Register"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.month_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.month_end(), "reqd": 1},
        {"fieldname":"standard", "label":"Standard", "fieldtype":"Link", "options":"Standard"},
        {"fieldname":"batch", "label":"Batch", "fieldtype":"Link", "options":"Batch"}
    ]
};
"""
with open(os.path.join(base_path, "monthly_attendance_register/monthly_attendance_register.py"), "w") as f: f.write(reg_py)
with open(os.path.join(base_path, "monthly_attendance_register/monthly_attendance_register.js"), "w") as f: f.write(reg_js)

# 9. Attendance Holiday Report
hol_py = common_imports + """
def execute(filters=None):
    columns = [
        {"fieldname": "holiday_date", "label": "Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "holiday_type", "label": "Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "reason", "label": "Reason", "fieldtype": "Data", "width": 250},
        {"fieldname": "scope", "label": "Scope", "fieldtype": "Data", "width": 150},
        {"fieldname": "standard", "label": "Standard", "fieldtype": "Data", "width": 100},
        {"fieldname": "batch", "label": "Batch", "fieldtype": "Data", "width": 100},
        {"fieldname": "owner", "label": "Created By", "fieldtype": "Data", "width": 150}
    ]
    
    cond = ""
    if filters.get("holiday_type"): cond += " AND holiday_type = %(holiday_type)s"
    if filters.get("standard"): cond += " AND (standard = %(standard)s OR scope='Entire School')"
    if filters.get("batch"): cond += " AND (batch = %(batch)s OR scope='Standard' OR scope='Entire School')"
    
    data = frappe.db.sql(f\"\"\"
        SELECT holiday_date, holiday_type, reason, scope, standard, batch, owner
        FROM `tabAttendance Holiday`
        WHERE holiday_date BETWEEN %(from_date)s AND %(to_date)s
        {cond}
        ORDER BY holiday_date DESC
    \"\"\", filters, as_dict=True)
    
    return columns, data
"""
hol_js = """
frappe.query_reports["Attendance Holiday Report"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.year_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.year_end(), "reqd": 1},
        {"fieldname":"holiday_type", "label":"Holiday Type", "fieldtype":"Select", "options":"\\nRain\\nGovernment Holiday\\nSchool Holiday\\nEmergency\\nOther"},
        {"fieldname":"standard", "label":"Standard", "fieldtype":"Link", "options":"Standard"},
        {"fieldname":"batch", "label":"Batch", "fieldtype":"Link", "options":"Batch"}
    ]
};
"""
with open(os.path.join(base_path, "attendance_holiday_report/attendance_holiday_report.py"), "w") as f: f.write(hol_py)
with open(os.path.join(base_path, "attendance_holiday_report/attendance_holiday_report.js"), "w") as f: f.write(hol_js)

