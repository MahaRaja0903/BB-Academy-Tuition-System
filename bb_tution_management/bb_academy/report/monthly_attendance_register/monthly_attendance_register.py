import frappe
from frappe.utils import getdate, add_days, get_first_day, get_last_day
from collections import defaultdict

def execute(filters=None):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    
    columns = [
        {"fieldname": "student", "label": "Student ID", "fieldtype": "Link", "options": "Student", "width": 120, "sticky": True},
        {"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 200, "sticky": True}
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
    batch_cond = f" AND current_batch = '{filters.get('batch')}'" if filters.get('batch') else ""
    gender_cond = f" AND gender = '{filters.get('gender')}'" if filters.get('gender') else ""
    
    # Get all matching active students
    students = frappe.db.sql(f"""
        SELECT name as student, student_name, standard, current_batch as batch
        FROM `tabStudent`
        WHERE status = 'Active' {std_cond} {batch_cond} {gender_cond}
    """, as_dict=True)
    
    students_map = {}
    for s in students:
        students_map[s.student] = {
            "student": s.student,
            "student_name": s.student_name,
            "standard": s.standard,
            "batch": s.batch,
            "present": 0, "absent": 0, "late": 0
        }

    std_cond2 = f" AND a.standard = '{filters.get('standard')}'" if filters.get('standard') else ""
    batch_cond2 = f" AND s.current_batch = '{filters.get('batch')}'" if filters.get('batch') else ""
    gender_cond2 = f" AND s.gender = '{filters.get('gender')}'" if filters.get('gender') else ""
    
    data = frappe.db.sql(f"""
        SELECT a.student, a.student_name, a.attendance_date, a.status, s.standard, s.current_batch as batch
        FROM `tabStudent Attendance` a
        JOIN `tabStudent` s ON a.student = s.name
        WHERE a.attendance_date BETWEEN %(from_date)s AND %(to_date)s
        {std_cond2} {batch_cond2} {gender_cond2}
    """, filters, as_dict=True)
    
    for r in data:
        stu = r.student
        if stu not in students_map:
            students_map[stu] = {
                "student": stu, 
                "student_name": r.student_name,
                "standard": r.standard,
                "batch": r.batch,
                "present": 0, "absent": 0, "late": 0
            }
            
        dt = r.attendance_date
        diff = (dt - from_date).days
        if 0 <= diff < days:
            stat_char = r.status[0] # P, A, L
            students_map[stu][f"day_{diff}"] = stat_char
            
            if stat_char == 'P': students_map[stu]["present"] += 1
            elif stat_char == 'A': students_map[stu]["absent"] += 1
            elif stat_char == 'L': students_map[stu]["late"] += 1
        
    # Fetch holidays
    holidays = frappe.db.sql("""
        SELECT holiday_date, scope, standard, batch 
        FROM `tabAttendance Holiday`
        WHERE holiday_date BETWEEN %(from_date)s AND %(to_date)s
    """, filters, as_dict=True)
    
    holidays_by_date = defaultdict(list)
    for h in holidays:
        hd = getdate(h.holiday_date)
        holidays_by_date[hd].append(h)
        
    out = []
    for stu, row in students_map.items():
        w = row["present"] + row["absent"] + row["late"]
        att = row["present"] + row["late"]
        row["pct"] = f"{round((att/w)*100, 1)}%" if w > 0 else "0%"
        
        # Fill missing with '-' or 'H'
        for i in range(days):
            col = f"day_{i}"
            if col not in row:
                d = add_days(from_date, i)
                is_holiday = False
                if d in holidays_by_date:
                    for h in holidays_by_date[d]:
                        if h.scope == 'Entire School':
                            is_holiday = True
                            break
                        elif h.scope == 'Standard' and h.standard == row.get('standard'):
                            is_holiday = True
                            break
                        elif h.scope == 'Standard + Batch' and h.standard == row.get('standard') and h.batch == row.get('batch'):
                            is_holiday = True
                            break
                row[col] = "H" if is_holiday else "-"
                
        out.append(row)
        
    out.sort(key=lambda x: x["student"])

    late_days = filters.get("late_days")
    absent_days = filters.get("absent_days")

    final_out = []
    for row in out:
        include = True
        if late_days not in (None, "") and row["late"] < int(late_days):
            include = False
        if absent_days not in (None, "") and row["absent"] < int(absent_days):
            include = False
            
        if include:
            final_out.append(row)

    return columns, final_out
