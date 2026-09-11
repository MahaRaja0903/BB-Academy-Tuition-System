import frappe
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    
    frappe.cache.hdel("doctype_meta", "BB SMS Settings")
    frappe.cache.delete_key("meta:BB SMS Settings")
    
    print("Deleted BB SMS Settings from Redis!")
