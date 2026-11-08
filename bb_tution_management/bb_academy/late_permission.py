import json

import frappe
from frappe.utils import cint, getdate, today

# The third Type on the Late Permission page. Parents tell the tuition ahead of
# time that the student will break a behaviour rule for a reason outside their
# control (the school bus runs late, the uniform is at the tailor's); the
# behaviour points they permit are excused for that day and are not mistakes.
DISCIPLINE_PERMISSION = "Discipline Permission"

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


def allowed_permission_reasons():
    """Behaviour Reasons BB Academy Settings allows to be granted as a
    Discipline Permission, in the master's display order. Disabled reasons are
    left out even when still listed."""
    names = frappe.get_all(
        "Student Behaviour Reason Item",
        filters={
            "parenttype": "BB Academy Settings",
            "parentfield": "discipline_permission_reasons",
        },
        pluck="behaviour_reason",
    )
    if not names:
        return []
    reasons = frappe.get_all(
        "Behaviour Reason",
        filters={"name": ["in", names], "disabled": 0},
        fields=["name", "reason_name", "severity", "display_order", "description"],
        limit_page_length=0,
    )
    reasons.sort(key=lambda r: (not r.display_order, r.display_order or 0, r.reason_name))
    return reasons


def permitted_reasons_map(students, date):
    """{student: [behaviour reasons permitted on `date`]} for `students`."""
    # Guards the window between a code deploy and the migrate that creates the
    # table: every Behaviour save comes through here.
    if not students or not frappe.db.table_exists(DISCIPLINE_PERMISSION):
        return {}
    rows = frappe.db.sql("""
        SELECT dp.student, i.behaviour_reason
        FROM `tabDiscipline Permission` dp
        INNER JOIN `tabStudent Behaviour Reason Item` i
            ON i.parent = dp.name AND i.parenttype = 'Discipline Permission'
        WHERE %(date)s BETWEEN dp.from_date AND dp.to_date
            AND dp.student IN %(students)s
        ORDER BY i.idx ASC
    """, {"date": getdate(date), "students": tuple(students)}, as_dict=True)
    out = {}
    for row in rows:
        out.setdefault(row.student, []).append(row.behaviour_reason)
    return out


def permitted_reasons(student, date):
    return permitted_reasons_map([student], date).get(student, [])


def permission_on(student, date, fields="name"):
    """The Discipline Permission covering `date` for `student`, if any."""
    date_obj = getdate(date)
    return frappe.db.get_value(
        DISCIPLINE_PERMISSION,
        {"student": student, "from_date": ["<=", date_obj], "to_date": [">=", date_obj]},
        fields,
        as_dict=not isinstance(fields, str),
    )


def excuse_behaviour_row(student, from_date, to_date):
    """Re-save the student's Behaviour rows from `from_date` to `to_date` that
    hold a reason now permitted, so the tracker drops it (see
    StudentPerformanceTracker.drop_permitted_reasons) and the Student Mistake
    Record follows. Saved without permission checks: it is a side effect of the
    permission grant the user is already allowed to make."""
    rows = frappe.get_all(
        "Student Performance Tracker",
        filters={
            "student": student,
            "category": "Behaviour",
            "date": ["between", [getdate(from_date), getdate(to_date)]],
        },
        fields=["name", "date"],
    )
    for row in rows:
        doc = frappe.get_doc("Student Performance Tracker", row.name)
        permitted = set(permitted_reasons(student, row.date))
        if any(r.behaviour_reason in permitted for r in doc.behaviour_reasons or []):
            doc.save(ignore_permissions=True)


@frappe.whitelist()
def get_discipline_permission_reasons():
    """The reasons the grant dialog offers."""
    if not frappe.has_permission(DISCIPLINE_PERMISSION, "read"):
        return []
    return allowed_permission_reasons()


@frappe.whitelist()
def get_students_for_late_permission(standard, batch, date, gender=None, permission_type="Late Permission"):
    doctype = DISCIPLINE_PERMISSION if permission_type == DISCIPLINE_PERMISSION else "Late Permission"
    if not frappe.has_permission(doctype, "read"):
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
    elif permission_type == DISCIPLINE_PERMISSION:
        permissions = frappe.get_all(
            DISCIPLINE_PERMISSION,
            filters={
                "student": ["in", student_ids],
                "from_date": ["<=", date_obj],
                "to_date": [">=", date_obj],
            },
            fields=["name", "student", "from_date", "to_date", "remarks", "parents_informed"],
        )
        perm_map = {p.student: p for p in permissions}
        reason_map = permitted_reasons_map(student_ids, date_obj)
        labels = dict(frappe.get_all(
            "Behaviour Reason",
            filters={"name": ["in", [r for rs in reason_map.values() for r in rs] or [""]]},
            fields=["name", "reason_name"],
            as_list=True,
        ))

        for s in students:
            p = perm_map.get(s.name)
            reasons = reason_map.get(s.name, []) if p else []
            s["has_permission"] = 1 if p else 0
            s["behaviour_reasons"] = reasons
            s["behaviour_reason_labels"] = [labels.get(r, r) for r in reasons]
            s["remarks"] = (p.remarks if p else "") or ""
            s["permission"] = p.name if p else ""
            s["from_date"] = str(p.from_date) if p else ""
            s["to_date"] = str(p.to_date) if p else ""
            s["parents_informed"] = cint(p.parents_informed) if p else 0
            s["attendance_status"] = s.get("attendance_status") or ""
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
def grant_late_permission(student, date, late_reason, parents_informed=0, time=None):
    """Grant (or re-grant) a late permission.

    `parents_informed` defaults to 0 to match the doctype: informing the parents
    is a separate action the user confirms, never something a grant assumes.
    """
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
        # Frappe stamps nowtime() onto every blank Time field during insert;
        # the controller's before_insert undoes that unless this flag says a
        # time was genuinely supplied. See LatePermission.before_insert.
        doc.flags.time_given = bool(time)
        doc.insert()

    return "success"


@frappe.whitelist()
def set_parents_informed(student, date, parents_informed, permission_type="Late Permission"):
    """Toggle the Parents Informed flag on an already-granted Late or
    Discipline Permission."""
    doctype = DISCIPLINE_PERMISSION if permission_type == DISCIPLINE_PERMISSION else "Late Permission"
    if not frappe.has_permission(doctype, "write"):
        frappe.throw("No permission")

    date_obj = getdate(date)
    if doctype == DISCIPLINE_PERMISSION:
        existing = permission_on(student, date_obj)
    else:
        existing = frappe.db.get_value(doctype, {"student": student, "date": date_obj}, "name")
    if not existing:
        frappe.throw(f"No {doctype} record found for this student on this date.")

    doc = frappe.get_doc(doctype, existing)
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
def grant_discipline_permission(
    student, from_date, to_date, behaviour_reasons, remarks=None, parents_informed=0, permission=None
):
    """Grant a Discipline Permission for the picked behaviour points from
    `from_date` to `to_date`, or update `permission` when editing one.
    Re-granting replaces the permitted points with the new pick."""
    if not frappe.has_permission(DISCIPLINE_PERMISSION, "write"):
        frappe.throw("No permission")

    if isinstance(behaviour_reasons, str):
        behaviour_reasons = json.loads(behaviour_reasons or "[]")
    rows = [{"behaviour_reason": r} for r in behaviour_reasons or []]

    doc = (
        frappe.get_doc(DISCIPLINE_PERMISSION, permission)
        if permission
        else frappe.new_doc(DISCIPLINE_PERMISSION)
    )
    doc.student = student
    doc.from_date = getdate(from_date)
    doc.to_date = getdate(to_date or from_date)
    doc.remarks = (remarks or "").strip() or None
    doc.parents_informed = cint(parents_informed)
    doc.set("behaviour_reasons", rows)
    doc.save()

    return "success"


@frappe.whitelist()
def revoke_discipline_permission(student, date):
    """Withdraw the permission covering `date`, for its whole date range. A
    Behaviour grade it already excused stays as it is; the teacher re-grades
    the student if the point should now count. To end it early, edit the End
    Date instead."""
    if not frappe.has_permission(DISCIPLINE_PERMISSION, "write"):
        frappe.throw("No permission")
    existing = permission_on(student, date)
    if existing:
        frappe.delete_doc(DISCIPLINE_PERMISSION, existing)
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
