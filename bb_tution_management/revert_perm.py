import frappe

def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    
    # Find all Custom DocPerms for DocType
    custom_perms = frappe.get_all("Custom DocPerm", filters={"parent": "DocType"}, pluck="name")
    
    for perm in custom_perms:
        frappe.delete_doc("Custom DocPerm", perm, ignore_permissions=True, force=True)
    
    frappe.db.commit()
    print(f"Deleted {len(custom_perms)} Custom DocPerm records for 'DocType'.")
