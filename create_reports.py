import sys
import os
import frappe

frappe.init(site='bb_academy.local')
frappe.connect()

def create_report(name, ref_doctype):
    if not frappe.db.exists("Report", name):
        doc = frappe.get_doc({
            "doctype": "Report",
            "report_name": name,
            "ref_doctype": ref_doctype,
            "report_type": "Script Report",
            "is_standard": "Yes",
            "module": "BB Academy"
        })
        doc.insert(ignore_permissions=True)
        print(f"Created report {name}")
    else:
        print(f"Report {name} already exists")

create_report("Student Wise Report", "Student")
create_report("Payment Wise Report", "Payment Entry")
create_report("Birthday Report", "Student")
create_report("Pending Balance Report", "Fee Invoice")

frappe.db.commit()
