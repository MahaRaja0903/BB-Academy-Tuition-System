import frappe
from frappe.model.meta import Meta
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    
    print("1. DB get_value:", frappe.db.get_value("DocType", "BB SMS Settings", "name"))
    print("2. Redis check:", frappe.cache.get_value("meta:BB SMS Settings") is not None)
    
    try:
        meta = Meta("BB SMS Settings")
        print("3. Meta() init succeeded!")
    except Exception as e:
        print(f"3. Meta() failed with {type(e)}")
        
    try:
        meta = frappe.get_meta("BB SMS Settings")
        print("4. get_meta() succeeded!")
    except Exception as e:
        print(f"4. get_meta() failed with {type(e)}")
