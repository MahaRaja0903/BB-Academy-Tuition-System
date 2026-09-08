import frappe

def run():
    # Remove Server Script
    if frappe.db.exists("Server Script", "Set Preferred WhatsApp Number"):
        frappe.delete_doc("Server Script", "Set Preferred WhatsApp Number")
        print("Deleted Server Script")
        
    # Remove Custom Field
    if frappe.db.exists("Custom Field", "Student-preferred_whatsapp_number"):
        frappe.delete_doc("Custom Field", "Student-preferred_whatsapp_number")
        print("Deleted Custom Field")
        
    frappe.db.commit()
