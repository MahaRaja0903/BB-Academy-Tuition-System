import frappe
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    meta = frappe.cache.hget("doctype_meta", "BB SMS Settings")
    if meta:
        print("FOUND IN REDIS doctype_meta!")
    else:
        print("NOT IN REDIS!")
