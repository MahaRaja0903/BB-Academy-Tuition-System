import frappe
from frappe.utils import getdate, add_days, get_first_day, get_last_day

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
    
    std_cond = f" AND a.standard = '{filters.get('standard')}'" if filters.get('standard') else ""
    batch_cond = f" AND s.current_batch = '{filters.get('batch')}'" if filters.get('batch') else ""
    
    data = frappe.db.sql(f"""
        SELECT a.student, a.student_name, a.attendance_date, a.status
        FROM `tabStudent Attendance` a
        JOIN `tabStudent` s ON a.student = s.name
        WHERE a.attendance_date BETWEEN %(from_date)s AND %(to_date)s
        {std_cond} {batch_cond}
    """, filters, as_dict=True)
    
    # Also fetch holidays to mark them
    # For simplicity, we query holidays and match them.
    holidays = frappe.db.sql("""
        SELECT holiday_date, scope, standard, batch 
        FROM `tabAttendance Holiday`
        WHERE holiday_date BETWEEN %(from_date)s AND %(to_date)s
    """, filters, as_dict=True)
    
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
