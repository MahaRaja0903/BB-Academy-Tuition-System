import frappe

def create():
    if frappe.db.exists("DocType", "Student Rejoin Log"):
        print("DocType already exists")
    else:
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Student Rejoin Log",
            "module": "BB Academy",
            "custom": 0,
            "istable": 0,
            "naming_rule": "Expression",
            "autoname": "format:REJOIN-{student}-{YYYY}-{MM}-{DD}",
            "fields": [
                {
                    "fieldname": "student",
                    "fieldtype": "Link",
                    "options": "Student",
                    "label": "Student",
                    "in_list_view": 1,
                    "reqd": 1
                },
                {
                    "fieldname": "student_name",
                    "fieldtype": "Data",
                    "label": "Student Name",
                    "fetch_from": "student.student_name",
                    "in_list_view": 1
                },
                {
                    "fieldname": "rejoined_date",
                    "fieldtype": "Date",
                    "label": "Rejoined Date",
                    "in_list_view": 1,
                    "reqd": 1
                },
                {
                    "fieldname": "discontinued_date",
                    "fieldtype": "Date",
                    "label": "Discontinued Date"
                },
                {
                    "fieldname": "discontinued_reason",
                    "fieldtype": "Small Text",
                    "label": "Discontinued Reason"
                }
            ],
            "permissions": [
                {
                    "role": "System Manager",
                    "read": 1,
                    "write": 1,
                    "create": 1,
                    "delete": 1
                },
                {
                    "role": "Administrator",
                    "read": 1,
                    "write": 1,
                    "create": 1,
                    "delete": 1
                }
            ]
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("DocType Created")

    student_dt = frappe.get_doc("DocType", "Student")
    fields = [f.fieldname for f in student_dt.fields]
    if "rejoined_date" not in fields:
        student_dt.append("fields", {
            "fieldname": "rejoined_date",
            "fieldtype": "Date",
            "label": "Rejoined Date",
            "insert_after": "discontinued_reason"
        })
        student_dt.save(ignore_permissions=True)
        print("rejoined_date added to Student")

