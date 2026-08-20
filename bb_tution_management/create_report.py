import frappe

def main():
    if not frappe.db.exists("Report", "Discount Report"):
        doc = frappe.new_doc("Report")
        doc.report_name = "Discount Report"
        doc.ref_doctype = "Fee Invoice"
        doc.report_type = "Script Report"
        doc.is_standard = "Yes"
        doc.module = "BB Academy"
        doc.insert()
        frappe.db.commit()
        print("Report created")
    else:
        print("Report already exists")
