import frappe

def create_doctype():
    if not frappe.db.exists("Role", "Attendance Manager"):
        frappe.get_doc({"doctype": "Role", "role_name": "Attendance Manager"}).insert()

    if not frappe.db.exists("DocType", "Late Permission"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Late Permission",
            "module": "BB Academy",
            "custom": 0,
            "naming_rule": "Expression",
            "autoname": "format:LP-{student}-{date}",
            "fields": [
                {"fieldname": "student", "fieldtype": "Link", "options": "Student", "label": "Student", "reqd": 1, "in_list_view": 1},
                {"fieldname": "student_name", "fieldtype": "Data", "label": "Student Name", "fetch_from": "student.student_name", "read_only": 1, "in_list_view": 1},
                {"fieldname": "date", "fieldtype": "Date", "label": "Date", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
                {"fieldname": "late_reason", "fieldtype": "Data", "label": "Late Reason", "reqd": 1, "in_list_view": 1},
                {"fieldname": "parents_informed", "fieldtype": "Check", "label": "Parents Informed", "default": 1}
            ],
            "permissions": [
                {"role": "Attendance Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
                {"role": "Administrator", "read": 1, "write": 1, "create": 1, "delete": 1}
            ]
        })
        doc.insert()
        print("Created Late Permission")
    else:
        print("Late Permission already exists")

if __name__ == "__main__":
    create_doctype()
