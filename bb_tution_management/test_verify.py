import frappe
from frappe.modules.utils import get_module_app

def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    try:
        from frappe.desk.desktop import get_workspace_sidebar_items
        items = get_workspace_sidebar_items()
        print("Workspace loaded successfully")
        import frappe.modules
        doctypes = frappe.modules.get_module_list("bb_academy")
        if "BB SMS Settings" in doctypes:
            print("ERROR: BB SMS Settings still in module list!")
        else:
            print("SUCCESS: BB SMS Settings is gone from module list!")
    except Exception as e:
        print("Exception:", str(e))
