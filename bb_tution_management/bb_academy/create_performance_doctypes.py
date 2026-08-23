import frappe

def create_doctypes():
    if not frappe.db.exists("Role", "Performance Manager"):
        frappe.get_doc({"doctype": "Role", "role_name": "Performance Manager"}).insert()
        print("Created Role Performance Manager")

    if not frappe.db.exists("DocType", "Student Performance Tracker"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Student Performance Tracker",
            "module": "BB Academy",
            "custom": 0,
            "naming_rule": "Expression",
            "autoname": "format:PERF-{student}-{date}",
            "fields": [
                {"fieldname": "student", "fieldtype": "Link", "options": "Student", "label": "Student", "reqd": 1, "in_list_view": 1},
                {"fieldname": "student_name", "fieldtype": "Data", "label": "Student Name", "fetch_from": "student.student_name", "read_only": 1, "in_list_view": 1},
                {"fieldname": "date", "fieldtype": "Date", "label": "Date", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
                
                {"fieldname": "study", "fieldtype": "Check", "label": "Study", "in_list_view": 1},
                {"fieldname": "study_performance", "fieldtype": "Select", "options": "Good\nBad\nPoor", "label": "Study Performance", "depends_on": "eval:doc.study==1"},
                
                {"fieldname": "test", "fieldtype": "Check", "label": "Test", "in_list_view": 1},
                {"fieldname": "test_performance", "fieldtype": "Select", "options": "Good\nBad\nPoor", "label": "Test Performance", "depends_on": "eval:doc.test==1"},
                
                {"fieldname": "maths_test", "fieldtype": "Check", "label": "Maths Test", "in_list_view": 1},
                {"fieldname": "maths_test_performance", "fieldtype": "Select", "options": "Good\nBad\nPoor", "label": "Maths Test Performance", "depends_on": "eval:doc.maths_test==1"},
                
                {"fieldname": "discipline", "fieldtype": "Check", "label": "Discipline", "in_list_view": 1},
                {"fieldname": "discipline_performance", "fieldtype": "Select", "options": "Good\nBad\nCritical", "label": "Discipline Performance", "depends_on": "eval:doc.discipline==1"},
                
                {"fieldname": "bad_activities", "fieldtype": "Small Text", "label": "Bad Activities", "depends_on": "eval:doc.discipline==1 && doc.discipline_performance=='Bad'"},
                {"fieldname": "critical_activities", "fieldtype": "Small Text", "label": "Critical Activities", "depends_on": "eval:doc.discipline==1 && doc.discipline_performance=='Critical'"}
            ],
            "permissions": [
                {"role": "Performance Manager", "read": 1, "write": 1, "create": 1, "email": 1, "print": 1, "export": 1, "report": 1, "share": 1},
                {"role": "Administrator", "read": 1, "write": 1, "create": 1, "delete": 1, "email": 1, "print": 1, "export": 1, "report": 1, "share": 1}
            ]
        })
        doc.insert()
        print("Created Student Performance Tracker")

if __name__ == "__main__":
    create_doctypes()
