import frappe
from frappe.utils import getdate, today

@frappe.whitelist()
def get_students_for_late_permission(standard, batch, date, gender=None):
    if not frappe.has_permission("Late Permission", "read"):
        frappe.throw("No permission to read")

    date_obj = getdate(date)

    gender_filter = " AND gender = %s" if gender else ""
    params = [standard, batch, date_obj]
    if gender:
        params.append(gender)

    students = frappe.db.sql(f"""
        SELECT name, student_name, gender, image
        FROM `tabStudent`
        WHERE status = 'Active'
          AND standard = %s
          AND current_batch = %s
          AND admission_date <= %s
          {gender_filter}
        ORDER BY student_name ASC
    """, tuple(params), as_dict=True)

    student_ids = [s.name for s in students]
    
    if not student_ids:
        return {"students": []}

    # get existing late permissions
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
