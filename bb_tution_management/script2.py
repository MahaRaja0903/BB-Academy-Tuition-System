import frappe
def run():
    frappe.get_doc('Fee Invoice', 'BB-INV-2026-00034').submit()
    frappe.db.commit()
