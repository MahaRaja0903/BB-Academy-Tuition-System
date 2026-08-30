import frappe
from frappe.utils import getdate, today

@frappe.whitelist()
def get_students_for_late_permission(standard, batch, date, gender=None, permission_type="Late Permission"):
    if not frappe.has_permission("Late Permission", "read"):
        frappe.throw("No permission to read")

    date_obj = getdate(date)

    # Build gender filter
    gender_filter = ""
    params = [standard, batch, date_obj]
    if gender:
        gender_filter = " AND s.gender = %s"
        params.append(gender)

    # Only fetch students who have attendance taken for this date
    # and whose attendance status is Present or Late (exclude Absent)
    students = frappe.db.sql(f"""
        SELECT s.name, s.student_name, s.gender, s.image,
               sa.status AS attendance_status,
               sa.early_out_time, sa.early_out_reason
        FROM `tabStudent` s
        INNER JOIN `tabStudent Attendance` sa
            ON sa.student = s.name
            AND sa.attendance_date = %s
            AND sa.status IN ('Present', 'Late')
        WHERE s.status = 'Active'
          AND s.standard = %s
          AND s.current_batch = %s
          {gender_filter}
        ORDER BY s.student_name ASC
    """, tuple([date_obj, standard, batch] + ([gender] if gender else [])), as_dict=True)

    student_ids = [s.name for s in students]
    
    if not student_ids:
        return {"students": []}

    if permission_type == "Early Out":
        # For Early Out mode, check if attendance already has early_out_time set
        for s in students:
            s["has_permission"] = 1 if s.get("early_out_time") else 0
            s["early_out_time"] = str(s.get("early_out_time") or "")
            s["early_out_reason"] = s.get("early_out_reason") or ""
    else:
        # For Late Permission mode, check existing Late Permission records
        permissions = frappe.db.sql("""
            SELECT student, late_reason, parents_informed
            FROM `tabLate Permission`
            WHERE date = %s AND student IN %s
        """, (date_obj, tuple(student_ids)), as_dict=True)
        
        perm_map = {p.student: p for p in permissions}

        for s in students:
            p = perm_map.get(s.name)
            s["has_permission"] = 1 if p else 0
            s["late_reason"] = p.late_reason if p else ""

    return {"students": students}

@frappe.whitelist()
def grant_late_permission(student, date, late_reason):
    if not frappe.has_permission("Late Permission", "write"):
        frappe.throw("No permission")
        
    date_obj = getdate(date)

    existing = frappe.db.get_value("Late Permission", {"student": student, "date": date_obj}, "name")
    if existing:
        doc = frappe.get_doc("Late Permission", existing)
        doc.late_reason = late_reason
        doc.save()
    else:
        doc = frappe.get_doc({
            "doctype": "Late Permission",
            "student": student,
            "date": date_obj,
            "late_reason": late_reason,
            "parents_informed": 1
        })
        doc.insert()
    
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
