import frappe
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    res = frappe.db.get_value("DocType", "BB SMS Settings", "*", as_dict=True)
    print("get_value:", res)
