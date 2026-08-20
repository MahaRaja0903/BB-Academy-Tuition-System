import frappe
from frappe.utils import getdate, today, add_days, get_first_day, get_last_day
import json

@frappe.whitelist()
def get_attendance_students(standard, batch, attendance_date):
    if not frappe.has_permission("Student Attendance", "read"):
        frappe.throw("No permission to read attendance")
        
    date_obj = getdate(attendance_date)
    
    # 1. Check for Holiday
    holiday = get_holiday_details(attendance_date, standard, batch)
    if holiday:
        return {"holiday": holiday, "students": [], "summary": {}}
        
    # 2. Get active students for the standard and batch, filtering by admission_date
    students = frappe.db.sql("""
        SELECT name, student_name, admission_date
        FROM `tabStudent`
        WHERE status = 'Active'
          AND standard = %s
          AND current_batch = %s
          AND admission_date <= %s
        ORDER BY name ASC
    """, (standard, batch, date_obj), as_dict=True)
    
    student_ids = [s.name for s in students]
    if not student_ids:
        return {"students": [], "summary": {"present": 0, "absent": 0, "late": 0, "pending": 0}, "holiday": None}
        
    # 3. Get Today's attendance
    today_att = frappe.db.sql("""
        SELECT student, status
        FROM `tabStudent Attendance`
        WHERE attendance_date = %s
          AND student IN %s
    """, (date_obj, tuple(student_ids)), as_dict=True)
    today_map = {r.student: r.status for r in today_att}
    
    # 4. Get Previous working day's attendance
    # Find the last attendance date before this date for any of these students
    prev_date = frappe.db.sql("""
        SELECT MAX(attendance_date) as dt
        FROM `tabStudent Attendance`
        WHERE attendance_date < %s
          AND student IN %s
    """, (date_obj, tuple(student_ids)))
    
    prev_map = {}
    if prev_date and prev_date[0][0]:
        prev_att = frappe.db.sql("""
            SELECT student, status
            FROM `tabStudent Attendance`
            WHERE attendance_date = %s
              AND student IN %s
        """, (prev_date[0][0], tuple(student_ids)), as_dict=True)
        prev_map = {r.student: r.status for r in prev_att}
        
    # 5. Get Monthly Stats
    first_day = get_first_day(date_obj)
    last_day = get_last_day(date_obj)
    monthly_att = frappe.db.sql("""
        SELECT student, status, count(name) as cnt
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %s AND %s
          AND student IN %s
          AND status IN ('Absent', 'Late')
        GROUP BY student, status
    """, (first_day, last_day, tuple(student_ids)), as_dict=True)
    
    monthly_map = {s: {"Absent": 0, "Late": 0} for s in student_ids}
    for row in monthly_att:
        monthly_map[row.student][row.status] = row.cnt
        
    # Combine data
    result_students = []
    summary = {"present": 0, "absent": 0, "late": 0, "pending": 0}
    
    for s in students:
        t_stat = today_map.get(s.name)
        if t_stat == 'Present': summary["present"] += 1
        elif t_stat == 'Absent': summary["absent"] += 1
        elif t_stat == 'Late': summary["late"] += 1
        else: summary["pending"] += 1
        
        result_students.append({
            "student_id": s.name,
            "student_name": s.student_name,
            "today_status": t_stat,
            "previous_status": prev_map.get(s.name, "N/A"),
            "monthly_absent": monthly_map[s.name]["Absent"],
            "monthly_late": monthly_map[s.name]["Late"]
        })
        
    return {
        "students": result_students,
        "summary": summary,
        "holiday": None
    }


@frappe.whitelist()
def save_student_attendance(student, attendance_date, status):
    if not frappe.has_permission("Student Attendance", "write"):
        frappe.throw("No permission to write attendance")
        
    # Prevent future attendance
    if getdate(attendance_date) > getdate(today()):
        frappe.throw("Cannot mark attendance for future dates")
        
    # Get student info
    stu = frappe.get_doc("Student", student)
    
    # Check if holiday
    holiday = get_holiday_details(attendance_date, stu.standard, stu.current_batch)
    if holiday:
        frappe.throw("Cannot mark attendance on a holiday")
        
    # Check existing
    existing = frappe.db.get_value("Student Attendance", {
        "student": student,
        "attendance_date": attendance_date
    }, "name")
    
    if existing:
        doc = frappe.get_doc("Student Attendance", existing)
        doc.status = status
        doc.save()
    else:
        doc = frappe.get_doc({
            "doctype": "Student Attendance",
            "student": student,
            "standard": stu.standard,
            "batch": stu.current_batch,
            "attendance_date": attendance_date,
            "status": status
        })
        doc.insert()
        
    # Return updated monthly stats
    date_obj = getdate(attendance_date)
    first_day = get_first_day(date_obj)
    last_day = get_last_day(date_obj)
    monthly_att = frappe.db.sql("""
        SELECT status, count(name) as cnt
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %s AND %s
          AND student = %s
          AND status IN ('Absent', 'Late')
        GROUP BY status
    """, (first_day, last_day, student), as_dict=True)
    
    monthly_map = {"Absent": 0, "Late": 0}
    for row in monthly_att:
        monthly_map[row.status] = row.cnt
        
    return {
        "status": "success",
        "monthly_absent": monthly_map["Absent"],
        "monthly_late": monthly_map["Late"]
    }

@frappe.whitelist()
def get_holiday_details(attendance_date, standard, batch):
    # Entire school
    school_hol = frappe.db.get_value("Attendance Holiday", {"holiday_date": attendance_date, "scope": "Entire School"}, ["holiday_type", "reason"], as_dict=True)
    if school_hol: return school_hol
    
    # Standard
    std_hol = frappe.db.get_value("Attendance Holiday", {"holiday_date": attendance_date, "scope": "Standard", "standard": standard}, ["holiday_type", "reason"], as_dict=True)
    if std_hol: return std_hol
    
    # Standard + Batch
    batch_hol = frappe.db.get_value("Attendance Holiday", {"holiday_date": attendance_date, "scope": "Standard + Batch", "standard": standard, "batch": batch}, ["holiday_type", "reason"], as_dict=True)
    if batch_hol: return batch_hol
    
    return None

@frappe.whitelist()
def assign_holiday(date, holiday_type, reason, scope, standard=None, batch=None):
    if not frappe.has_permission("Attendance Holiday", "create"):
        frappe.throw("No permission to create holiday")
        
    doc = frappe.get_doc({
        "doctype": "Attendance Holiday",
        "holiday_date": date,
        "holiday_type": holiday_type,
        "reason": reason,
        "scope": scope,
        "standard": standard,
        "batch": batch
    })
    doc.insert()
    return doc.name

@frappe.whitelist()
def get_attendance_dashboard():
    td = getdate(today())
    sevendays_ago = add_days(td, -6)
    
    new_students = frappe.db.count("Student", {"admission_date": ["between", [sevendays_ago, td]], "status": "Active"})
    today_absent = frappe.db.count("Student Attendance", {"attendance_date": td, "status": "Absent"})
    
    # Absent > 5 Days in current month or academic year?
    # Requirement: "Prefer current academic year or current academic year-to-date. Make this configurable if possible."
    # Let's use current month to make it simple and performant
    first_day = get_first_day(td)
    last_day = get_last_day(td)
    
    absent_5_plus = frappe.db.sql("""
        SELECT COUNT(*) FROM (
            SELECT student FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %s AND %s AND status = 'Absent'
            GROUP BY student HAVING count(name) >= 5
        ) AS t
    """, (first_day, last_day))[0][0]
    
    late_5_plus = frappe.db.sql("""
        SELECT COUNT(*) FROM (
            SELECT student FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %s AND %s AND status = 'Late'
            GROUP BY student HAVING count(name) >= 5
        ) AS t
    """, (first_day, last_day))[0][0]
    
    # Today summary
    summary_raw = frappe.db.sql("""
        SELECT status, count(name) as cnt
        FROM `tabStudent Attendance`
        WHERE attendance_date = %s
        GROUP BY status
    """, (td,), as_dict=True)
    
    summary = {"present": 0, "absent": 0, "late": 0, "pending": 0}
    for row in summary_raw:
        if row.status == "Present": summary["present"] = row.cnt
        elif row.status == "Absent": summary["absent"] = row.cnt
        elif row.status == "Late": summary["late"] = row.cnt
        
    total_active = frappe.db.count("Student", {"status": "Active", "admission_date": ["<=", td]})
    summary["pending"] = total_active - (summary["present"] + summary["absent"] + summary["late"])
    
    return {
        "new_students": new_students,
        "today_absent": today_absent,
        "absent_5_plus": absent_5_plus,
        "late_5_plus": late_5_plus,
        "today_summary": summary
    }


@frappe.whitelist()
def get_attendance_dashboard_data(academic_year=None, standard=None, batch=None, date=None):
    if not date:
        date = today()
        
    date_obj = getdate(date)
    first_day_month = get_first_day(date_obj)
    last_day_month = get_last_day(date_obj)
    
    # Base filters
    std_filter = " AND standard = %(standard)s " if standard else ""
    batch_filter = " AND current_batch = %(batch)s " if batch else ""
    
    # 1. New Students
    sevendays_ago = add_days(date_obj, -6)
    new_students_query = f"""
        SELECT COUNT(name) FROM `tabStudent` 
        WHERE status = 'Active' 
        AND admission_date BETWEEN %(sevendays_ago)s AND %(date)s
        {std_filter} {batch_filter}
    """
    new_students = frappe.db.sql(new_students_query, {
        "sevendays_ago": sevendays_ago, "date": date, "standard": standard, "batch": batch
    })[0][0]
    
    # 2. Today's Absent
    att_std_filter = " AND standard = %(standard)s " if standard else ""
    att_batch_filter = " AND batch = %(batch)s " if batch else ""
    today_absent_query = f"""
        SELECT COUNT(name) FROM `tabStudent Attendance`
        WHERE attendance_date = %(date)s AND status = 'Absent'
        {att_std_filter} {att_batch_filter}
    """
    today_absent = frappe.db.sql(today_absent_query, {
        "date": date, "standard": standard, "batch": batch
    })[0][0]
    
    # 3. Absent 5+ and Late 5+ (This month)
    abs_5_query = f"""
        SELECT COUNT(*) FROM (
            SELECT student FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s AND status = 'Absent'
            {att_std_filter} {att_batch_filter}
            GROUP BY student HAVING count(name) >= 5
        ) AS t
    """
    absent_5_plus = frappe.db.sql(abs_5_query, {
        "first_day": first_day_month, "last_day": last_day_month, "standard": standard, "batch": batch
    })[0][0]
    
    late_5_query = f"""
        SELECT COUNT(*) FROM (
            SELECT student FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s AND status = 'Late'
            {att_std_filter} {att_batch_filter}
            GROUP BY student HAVING count(name) >= 5
        ) AS t
    """
    late_5_plus = frappe.db.sql(late_5_query, {
        "first_day": first_day_month, "last_day": last_day_month, "standard": standard, "batch": batch
    })[0][0]
    
    # Today Summary Distribution
    summary_raw = frappe.db.sql(f"""
        SELECT status, count(name) as cnt
        FROM `tabStudent Attendance`
        WHERE attendance_date = %(date)s
        {att_std_filter} {att_batch_filter}
        GROUP BY status
    """, {"date": date, "standard": standard, "batch": batch}, as_dict=True)
    
    today_summary = {"present": 0, "absent": 0, "late": 0, "pending": 0}
    for row in summary_raw:
        if row.status == "Present": today_summary["present"] = row.cnt
        elif row.status == "Absent": today_summary["absent"] = row.cnt
        elif row.status == "Late": today_summary["late"] = row.cnt
        
    total_active = frappe.db.sql(f"""
        SELECT COUNT(name) FROM `tabStudent`
        WHERE status = 'Active' AND admission_date <= %(date)s
        {std_filter} {batch_filter}
    """, {"date": date, "standard": standard, "batch": batch})[0][0]
    
    today_summary["pending"] = total_active - (today_summary["present"] + today_summary["absent"] + today_summary["late"])
    today_summary["total"] = total_active
    
    # Top 10 Absent
    top_absent = frappe.db.sql(f"""
        SELECT student, student_name, count(name) as absent_count
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s AND status = 'Absent'
        {att_std_filter} {att_batch_filter}
        GROUP BY student, student_name
        ORDER BY absent_count DESC
        LIMIT 10
    """, {"first_day": first_day_month, "last_day": last_day_month, "standard": standard, "batch": batch}, as_dict=True)
    
    # Top 10 Late
    top_late = frappe.db.sql(f"""
        SELECT student, student_name, count(name) as late_count
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s AND status = 'Late'
        {att_std_filter} {att_batch_filter}
        GROUP BY student, student_name
        ORDER BY late_count DESC
        LIMIT 10
    """, {"first_day": first_day_month, "last_day": last_day_month, "standard": standard, "batch": batch}, as_dict=True)

    # Standard Summary (Bar chart)
    # Only if standard filter is empty
    standard_summary = []
    batch_summary = []
    if not standard:
        standard_summary = frappe.db.sql(f"""
            SELECT standard, status, count(name) as cnt
            FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s
            GROUP BY standard, status
        """, {"first_day": first_day_month, "last_day": last_day_month}, as_dict=True)
    else:
        batch_summary = frappe.db.sql(f"""
            SELECT batch, status, count(name) as cnt
            FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s
            {att_std_filter}
            GROUP BY batch, status
        """, {"first_day": first_day_month, "last_day": last_day_month, "standard": standard}, as_dict=True)
        
    # Last 30 Days Trend
    thirty_days_ago = add_days(date_obj, -29)
    trend_raw = frappe.db.sql(f"""
        SELECT attendance_date, status, count(name) as cnt
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(thirty_days)s AND %(date)s
        {att_std_filter} {att_batch_filter}
        GROUP BY attendance_date, status
        ORDER BY attendance_date ASC
    """, {"thirty_days": thirty_days_ago, "date": date, "standard": standard, "batch": batch}, as_dict=True)
    
    return {
        "new_students": new_students,
        "today_absent": today_absent,
        "absent_5_plus": absent_5_plus,
        "late_5_plus": late_5_plus,
        "today_summary": today_summary,
        "top_absent": top_absent,
        "top_late": top_late,
        "standard_summary": standard_summary,
        "batch_summary": batch_summary,
        "trend_raw": trend_raw
    }

