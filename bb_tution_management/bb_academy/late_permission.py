import frappe
from frappe.utils import cint, getdate, today

def _format_time(value):
    """Normalise a Time field to zero-padded "HH:MM".

    MySQL TIME columns come back as a timedelta, whose str() drops the leading
    zero ("9:05:00"). `<input type="time">` silently ignores such a value, so
    the field would render blank when editing an existing record.
    """
    if not value:
        return ""
    if isinstance(value, str):
        return value[:5]
    total_seconds = getattr(value, "total_seconds", None)
    if total_seconds is None:
        # datetime.time
        return f"{value.hour:02d}:{value.minute:02d}"
    total = int(total_seconds())
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"


@frappe.whitelist()
def get_students_for_late_permission(standard, batch, date, gender=None, permission_type="Late Permission"):
    if not frappe.has_permission("Late Permission", "read"):
        frappe.throw("No permission to read")

    date_obj = getdate(date)

    gender_filter = " AND s.gender = %(gender)s" if gender else ""

    # Early Out acts on an existing attendance record, so it only lists students
    # whose attendance is already marked. "Early Outs" must stay in this list:
    # granting flips the status to it, and without it the row would disappear
    # and Revoke would be unreachable.
    #
    # Late Permission is granted independently of attendance (it can be recorded
    # before the student is marked), so it lists every active student in the
    # batch and simply reports attendance_status as NULL when not yet marked.
    if permission_type == "Early Out":
        attendance_join = """
            INNER JOIN `tabStudent Attendance` sa
                ON sa.student = s.name
                AND sa.attendance_date = %(date)s
                AND sa.status IN ('Present', 'Late', 'Early Outs')
        """
    else:
        attendance_join = """
            LEFT JOIN `tabStudent Attendance` sa
                ON sa.student = s.name
                AND sa.attendance_date = %(date)s
        """

    # Batch matching mirrors attendance.get_attendance_students so both screens
    # agree on who belongs to a batch on a given day, including temporary
    # attendance-batch reassignments.
    students = frappe.db.sql(f"""
        SELECT s.name, s.student_name, s.gender, s.image,
               sa.status AS attendance_status,
               sa.early_out_time, sa.early_out_reason
        FROM `tabStudent` s
        {attendance_join}
        WHERE s.status = 'Active'
          AND s.standard = %(standard)s
          AND (
              (IFNULL(s.attendance_batch_set, 0) = 1 AND s.attendance_batch = %(batch)s)
              OR (IFNULL(s.attendance_batch_set, 0) = 0 AND s.current_batch = %(batch)s)
          )
          AND s.admission_date <= %(date)s
          {gender_filter}
        ORDER BY s.student_name ASC
    """, {
        "date": date_obj,
        "standard": standard,
        "batch": batch,
        "gender": gender,
    }, as_dict=True)

    student_ids = [s.name for s in students]
    
    if not student_ids:
        return {"students": []}

    if permission_type == "Early Out":
        # For Early Out mode, check if attendance already has early_out_time set
        for s in students:
            s["has_permission"] = 1 if s.get("early_out_time") else 0
            s["early_out_time"] = _format_time(s.get("early_out_time"))
            s["early_out_reason"] = s.get("early_out_reason") or ""
    else:
        # For Late Permission mode, check existing Late Permission records
        permissions = frappe.db.sql("""
            SELECT student, late_reason, parents_informed, `time`
            FROM `tabLate Permission`
            WHERE date = %s AND student IN %s
        """, (date_obj, tuple(student_ids)), as_dict=True)

        perm_map = {p.student: p for p in permissions}

        for s in students:
            p = perm_map.get(s.name)
            s["has_permission"] = 1 if p else 0
            s["late_reason"] = p.late_reason if p else ""
            # Surfaced so the UI can show and toggle the Parents Informed flag
            s["parents_informed"] = cint(p.parents_informed) if p else 0
            s["time"] = _format_time(p.time) if p else ""
            s["attendance_status"] = s.get("attendance_status") or ""

    return {"students": students}

@frappe.whitelist()
def grant_late_permission(student, date, late_reason, parents_informed=1, time=None):
    if not frappe.has_permission("Late Permission", "write"):
        frappe.throw("No permission")

    date_obj = getdate(date)
    parents_informed = cint(parents_informed)
    # Optional on the doctype: blank clears any previously recorded time.
    time = (time or "").strip() or None

    existing = frappe.db.get_value("Late Permission", {"student": student, "date": date_obj}, "name")
    if existing:
        doc = frappe.get_doc("Late Permission", existing)
        doc.late_reason = late_reason
        doc.parents_informed = parents_informed
        doc.time = time
        doc.save()
    else:
        doc = frappe.get_doc({
            "doctype": "Late Permission",
            "student": student,
            "date": date_obj,
            "late_reason": late_reason,
            "parents_informed": parents_informed,
            "time": time
        })
        doc.insert()

    return "success"


@frappe.whitelist()
def set_parents_informed(student, date, parents_informed):
    """Toggle the Parents Informed flag on an already-granted Late Permission."""
    if not frappe.has_permission("Late Permission", "write"):
        frappe.throw("No permission")

    date_obj = getdate(date)
    existing = frappe.db.get_value("Late Permission", {"student": student, "date": date_obj}, "name")
    if not existing:
        frappe.throw("No Late Permission record found for this student on this date.")

    doc = frappe.get_doc("Late Permission", existing)
    doc.parents_informed = cint(parents_informed)
    doc.save()

    return "success"
    
@frappe.whitelist()
def revoke_late_permission(student, date):
    if not frappe.has_permission("Late Permission", "write"):
        frappe.throw("No permission")
    date_obj = getdate(date)
    existing = frappe.db.get_value("Late Permission", {"student": student, "date": date_obj}, "name")
    if existing:
        frappe.delete_doc("Late Permission", existing)
    return "success"

@frappe.whitelist()
def grant_early_out(student, date, early_out_time, early_out_reason):
    if not frappe.has_permission("Student Attendance", "write"):
        frappe.throw("No permission")

    date_obj = getdate(date)

    att_name = frappe.db.get_value("Student Attendance", {
        "student": student,
        "attendance_date": date_obj,
        "status": ["in", ["Present", "Late"]]
    }, "name")

    if not att_name:
        frappe.throw("No attendance record found for this student on this date.")

    doc = frappe.get_doc("Student Attendance", att_name)
    doc.status = "Early Outs"
    doc.early_out_time = early_out_time
    doc.early_out_reason = early_out_reason
    doc.save()

    return "success"

@frappe.whitelist()
def revoke_early_out(student, date):
    if not frappe.has_permission("Student Attendance", "write"):
        frappe.throw("No permission")

    date_obj = getdate(date)

    att_name = frappe.db.get_value("Student Attendance", {
        "student": student,
        "attendance_date": date_obj,
        "status": "Early Outs"
    }, "name")

    if not att_name:
        frappe.throw("No early out record found for this student.")

    doc = frappe.get_doc("Student Attendance", att_name)
    doc.status = "Present"
    doc.early_out_time = None
    doc.early_out_reason = None
    doc.save()

    return "success"
