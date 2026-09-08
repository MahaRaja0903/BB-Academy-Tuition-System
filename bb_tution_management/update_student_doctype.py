import frappe

def run():
    doc = frappe.get_doc("DocType", "Student")
    
    # Check if field already exists
    exists = False
    for d in doc.fields:
        if d.fieldname == "preferred_whatsapp_number":
            exists = True
            break
            
    if not exists:
        # Find index to insert after preferred_mobile_number
        idx = 0
        for i, d in enumerate(doc.fields):
            if d.fieldname == "preferred_mobile_number":
                idx = i + 1
                break
                
        doc.insert(idx, "fields", {
            "fieldname": "preferred_whatsapp_number",
            "fieldtype": "Data",
            "label": "Preferred WhatsApp Number",
            "read_only": 1,
            "hidden": 1
        })
        doc.save()
        print("Field preferred_whatsapp_number added to Student DocType.")
    else:
        print("Field already exists.")
        
    frappe.db.commit()
