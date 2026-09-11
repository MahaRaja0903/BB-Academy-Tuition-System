import frappe
from werkzeug.test import Client
from frappe.app import application
import json

def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    
    draft = frappe.get_last_doc("Fee Invoice", filters={"docstatus": 0})
    doc_dict = draft.as_dict()
    doc_dict["__last_sync_on"] = frappe.utils.now()
    doc_dict["modified"] = doc_dict.get("modified")
    doc_str = frappe.as_json(doc_dict)
    
    client = Client(application)
    
    user = frappe.get_doc("User", "staff@gmail.com")
    if not user.api_secret:
        user.api_secret = frappe.generate_hash(length=15)
        user.save(ignore_permissions=True)
        frappe.db.commit()
    
    token = f"token {user.api_key}:{user.get_password('api_secret')}"

    response = client.post(
        "/api/method/frappe.desk.form.save.savedocs",
        data={"doc": doc_str, "action": "Submit"},
        headers={
            "X-Frappe-Site-Name": "bbacademy.dreamtechsolution.com",
            "Authorization": token
        }
    )
    print("STATUS:", response.status_code)
    try:
        data = response.data.decode()
        print("BODY:", data)
    except:
        pass
