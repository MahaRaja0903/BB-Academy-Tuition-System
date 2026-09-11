import frappe
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    try:
        from frappe.modules import get_doctype_module, get_module_path
        module = get_doctype_module("BB SMS Settings")
        print(f"Module: {module}")
        import os
        path = os.path.join(get_module_path(module), "doctype", frappe.scrub("BB SMS Settings"))
        print(f"Path: {path}")
        print(f"Path exists: {os.path.exists(path)}")
    except Exception as e:
        print(e)
