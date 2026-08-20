import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def create_reports():
    reports = [
        "Daily Attendance Report",
        "Student Attendance History",
        "Monthly Attendance Report",
        "Standard and Batch Attendance Summary",
        "Absent Student Report",
        "Late Entry Report",
        "Attendance Defaulters",
        "Monthly Attendance Register",
        "Attendance Holiday Report"
    ]
    
    for r in reports:
        if not frappe.db.exists("Report", r):
            doc = frappe.get_doc({
                "doctype": "Report",
                "report_name": r,
                "ref_doctype": "Student Attendance" if "Holiday" not in r else "Attendance Holiday",
                "report_type": "Script Report",
                "is_standard": "Yes",
                "module": "BB Academy"
            })
            doc.insert()
            print(f"Created Script Report {r}")
        else:
            # Update existing to Script Report
            frappe.db.set_value("Report", r, "report_type", "Script Report")
            print(f"Updated {r} to Script Report")

if __name__ == "__main__":
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    create_reports()
    frappe.db.commit()
    frappe.destroy()
