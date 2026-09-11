import frappe
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    res = frappe.db.sql("SELECT name, module FROM tabDocType WHERE name='BB SMS Settings'")
    print(res)
