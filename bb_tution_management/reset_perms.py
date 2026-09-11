import frappe
from frappe.permissions import reset_custom_permissions

def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    
    reset_custom_permissions("DocType")
    frappe.db.commit()
    print("Permissions reset for DocType.")
