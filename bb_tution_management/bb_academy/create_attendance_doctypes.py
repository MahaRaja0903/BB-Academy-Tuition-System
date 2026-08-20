import frappe

def create_doctypes():
    # Create Role if not exists
    if not frappe.db.exists("Role", "Attendance Manager"):
        frappe.get_doc({"doctype": "Role", "role_name": "Attendance Manager"}).insert()
        print("Created Role Attendance Manager")

    # 1. Student Attendance
    if not frappe.db.exists("DocType", "Student Attendance"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Student Attendance",
            "module": "BB Academy",
            "custom": 0,
            "naming_rule": "Expression",
            "autoname": "format:ATT-{student}-{attendance_date}",
            "fields": [
                {"fieldname": "student", "fieldtype": "Link", "options": "Student", "label": "Student", "reqd": 1, "in_list_view": 1},
                {"fieldname": "student_name", "fieldtype": "Data", "label": "Student Name", "fetch_from": "student.student_name", "read_only": 1, "in_list_view": 1},
                {"fieldname": "standard", "fieldtype": "Link", "options": "Standard", "label": "Standard", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
                {"fieldname": "batch", "fieldtype": "Link", "options": "Batch", "label": "Batch", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
                {"fieldname": "attendance_date", "fieldtype": "Date", "label": "Attendance Date", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
                {"fieldname": "status", "fieldtype": "Select", "options": "Present\nAbsent\nLate", "label": "Status", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
                {"fieldname": "remarks", "fieldtype": "Small Text", "label": "Remarks"}
            ],
            "permissions": [
                {"role": "Attendance Manager", "read": 1, "write": 1, "create": 1, "email": 1, "print": 1, "export": 1, "report": 1, "share": 1},
                {"role": "Administrator", "read": 1, "write": 1, "create": 1, "delete": 1, "email": 1, "print": 1, "export": 1, "report": 1, "share": 1}
            ]
        })
        doc.insert()
        print("Created Student Attendance")

    # 2. Attendance Holiday
    if not frappe.db.exists("DocType", "Attendance Holiday"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Attendance Holiday",
            "module": "BB Academy",
            "custom": 0,
            "naming_rule": "Expression",
            "autoname": "format:HOL-{holiday_date}",
            "fields": [
                {"fieldname": "holiday_date", "fieldtype": "Date", "label": "Holiday Date", "reqd": 1, "in_list_view": 1},
                {"fieldname": "holiday_type", "fieldtype": "Select", "options": "Rain\nGovernment Holiday\nSchool Holiday\nEmergency\nOther", "label": "Holiday Type", "reqd": 1, "in_list_view": 1},
                {"fieldname": "reason", "fieldtype": "Small Text", "label": "Reason", "reqd": 1},
                {"fieldname": "scope", "fieldtype": "Select", "options": "Entire School\nStandard\nStandard + Batch", "label": "Scope", "reqd": 1, "in_list_view": 1},
                {"fieldname": "standard", "fieldtype": "Link", "options": "Standard", "label": "Standard", "depends_on": "eval:in_list(['Standard', 'Standard + Batch'], doc.scope)"},
                {"fieldname": "batch", "fieldtype": "Link", "options": "Batch", "label": "Batch", "depends_on": "eval:doc.scope=='Standard + Batch'"}
            ],
            "permissions": [
                {"role": "Attendance Manager", "read": 1, "write": 1, "create": 1},
                {"role": "Administrator", "read": 1, "write": 1, "create": 1, "delete": 1}
            ]
        })
        doc.insert()
        print("Created Attendance Holiday")
        
