import frappe

def run():
    # 1. Custom Field
    if not frappe.db.exists("Custom Field", "Student-preferred_whatsapp_number"):
        cf = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Student",
            "fieldname": "preferred_whatsapp_number",
            "label": "Preferred WhatsApp Number",
            "fieldtype": "Data",
            "insert_after": "preferred_mobile_number",
            "read_only": 1,
            "hidden": 1
        })
        cf.insert()
        print("Custom Field created.")
    else:
        print("Custom Field already exists.")
    
    # 2. Server Script
    if not frappe.db.exists("Server Script", "Set Preferred WhatsApp Number"):
        script = frappe.get_doc({
            "doctype": "Server Script",
            "name": "Set Preferred WhatsApp Number",
            "script_type": "DocType Event",
            "reference_doctype": "Student",
            "doctype_event": "Before Save",
            "script": '''if doc.preferred_mobile_number == "Father":
    doc.preferred_whatsapp_number = doc.father_mobile_number
elif doc.preferred_mobile_number == "Mother":
    doc.preferred_whatsapp_number = doc.mother_mobile_number
else:
    doc.preferred_whatsapp_number = doc.father_mobile_number or doc.mother_mobile_number''',
            "disabled": 0
        })
        script.insert()
        print("Server Script created.")
    else:
        print("Server Script already exists.")
        
    # Templates
    joining_template = frappe.db.get_value("WhatsApp Templates", {"actual_name": "student_joining_message-en"}, "name")
    birthday_template = frappe.db.get_value("WhatsApp Templates", {"actual_name": "birthday_wishes-en"}, "name")
    
    if not joining_template:
        joining_template = frappe.db.get_value("WhatsApp Templates", "student_joining_message-en", "name")
    if not birthday_template:
        birthday_template = frappe.db.get_value("WhatsApp Templates", "birthday_wishes-en", "name")
        
    print(f"Templates found: Joining={joining_template}, Birthday={birthday_template}")
    
    if joining_template and not frappe.db.exists("WhatsApp Notification", "Student Joining Notification"):
        frappe.get_doc({
            "doctype": "WhatsApp Notification",
            "notification_name": "Student Joining Notification",
            "notification_type": "DocType Event",
            "reference_doctype": "Student",
            "doctype_event": "After Insert",
            "field_name": "preferred_whatsapp_number",
            "template": joining_template,
            "disabled": 0
        }).insert()
        print("Joining Notification created.")
        
    if birthday_template and not frappe.db.exists("WhatsApp Notification", "Student Birthday Wishes"):
        frappe.get_doc({
            "doctype": "WhatsApp Notification",
            "notification_name": "Student Birthday Wishes",
            "notification_type": "Scheduler Event",
            "reference_doctype": "Student",
            "event_frequency": "Daily",
            "template": birthday_template,
            "disabled": 0,
            "condition": """
students = frappe.db.sql('''
    SELECT name, student_name, father_mobile_number, mother_mobile_number, preferred_mobile_number
    FROM `tabStudent` 
    WHERE status='Active' 
      AND MONTH(date_of_birth) = MONTH(CURDATE()) 
      AND DAY(date_of_birth) = DAY(CURDATE())
''', as_dict=True)

data_list = []
for st in students:
    if st.preferred_mobile_number == "Father":
        phone = st.father_mobile_number
    elif st.preferred_mobile_number == "Mother":
        phone = st.mother_mobile_number
    else:
        phone = st.father_mobile_number or st.mother_mobile_number
        
    if phone:
        data_list.append({
            "name": st.name,
            "phone_no": phone
        })

doc.set("_data_list", data_list)
"""
        }).insert()
        print("Birthday Notification created.")
        
    frappe.db.commit()

