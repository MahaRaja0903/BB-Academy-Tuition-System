import frappe

def create_page():
    if frappe.db.exists("Page", "late_permission_manager"):
        frappe.delete_doc("Page", "late_permission_manager")
    if frappe.db.exists("Page", "late-permission-manager"):
        frappe.delete_doc("Page", "late-permission-manager")
    if frappe.db.exists("Page", "late_permission"):
        frappe.delete_doc("Page", "late_permission")

    page = frappe.get_doc({
        "doctype": "Page",
        "page_name": "late_permission",
        "module": "BB Academy",
        "title": "Late and Early Out Attendance",
        "roles": [{"role": "System Manager"}, {"role": "Administrator"}, {"role": "Attendance Manager"}]
    })
    page.insert()
    print("Created Page late_permission")

if __name__ == "__main__":
    create_page()
