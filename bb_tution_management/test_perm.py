import frappe
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    
    frappe.set_user("Administrator")
    print("Administrator can create DocType:", frappe.has_permission("DocType", "create"))
    
    frappe.set_user("staff@gmail.com")
    print("Staff can create DocType:", frappe.has_permission("DocType", "create"))
