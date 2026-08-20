import frappe

def create_pages():
    for page_name in ["attendance-manager", "attendance-dashboard"]:
        if not frappe.db.exists("Page", page_name):
            doc = frappe.get_doc({
                "doctype": "Page",
                "page_name": page_name,
                "title": page_name.replace("-", " ").title(),
                "module": "BB Academy",
                "standard": "Yes",
                "roles": [{"role": "Attendance Manager"}, {"role": "System Manager"}]
            })
            doc.insert()
            print(f"Created Page {page_name}")
