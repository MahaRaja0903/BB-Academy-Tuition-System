import frappe
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    
    # Check if Receptionist already has DocType read permission
    exists = frappe.db.exists("Custom DocPerm", {"parent": "DocType", "role": "Receptionist"})
    if not exists:
        # We can just add it to tabDocPerm or create a Custom DocPerm
        doc = frappe.new_doc("Custom DocPerm")
        doc.parent = "DocType"
        doc.role = "Receptionist"
        doc.read = 1
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Added Custom DocPerm for Receptionist on DocType")
    else:
        print("Already exists")
