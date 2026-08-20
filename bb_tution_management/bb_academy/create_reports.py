import frappe

def create_reports():
    reports = [
        {
            "report_name": "Daily Attendance",
            "ref_doctype": "Student Attendance",
            "report_type": "Report Builder",
            "is_standard": "Yes",
            "module": "BB Academy"
        },
        {
            "report_name": "Student Attendance",
            "ref_doctype": "Student Attendance",
            "report_type": "Report Builder",
            "is_standard": "Yes",
            "module": "BB Academy"
        },
        {
            "report_name": "Monthly Attendance",
            "ref_doctype": "Student Attendance",
            "report_type": "Report Builder",
            "is_standard": "Yes",
            "module": "BB Academy"
        }
    ]
    
    for r in reports:
        if not frappe.db.exists("Report", r["report_name"]):
            doc = frappe.get_doc({
                "doctype": "Report",
                **r
            })
            doc.insert()
            print(f"Created Report {r['report_name']}")

