import frappe
def patch_whatsapp():
    doc = frappe.get_doc('WhatsApp Notification', 'Student Joining Notification')
    doc.fields = []
    for f in ['student_name', 'standard', 'current_batch', 'admission_date', 'student_name']:
        doc.append('fields', {'field_name': f})
    doc.save(ignore_permissions=True)
    frappe.db.commit()

