import frappe
import json
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    meta = frappe.get_meta("BB SMS Settings")
    print(json.dumps(meta.as_dict(), default=str, indent=2))
