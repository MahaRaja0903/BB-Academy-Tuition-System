import frappe
from frappe.permissions import check_doctype_permission
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    frappe.set_user("staff@gmail.com")
    try:
        check_doctype_permission("DocType", "read")
    except Exception as e:
        import json
        print("MESSAGES:", frappe.message_log)
