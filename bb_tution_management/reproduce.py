import frappe
from frappe.desk.form.save import savedocs
import traceback
import json

def run():
    frappe.set_user("staff@gmail.com")
    # find an existing draft
    draft = frappe.get_last_doc("Fee Invoice", filters={"docstatus": 0})
    if not draft: return
    doc_dict = draft.as_dict()
    # To bypass TimestampMismatchError
    doc_dict["__last_sync_on"] = frappe.utils.now()
    doc_dict["modified"] = doc_dict.get("modified")
    doc_str = frappe.as_json(doc_dict)
    
    try:
        savedocs(doc_str, 'Submit')
        print("Success")
    except Exception as e:
        print(traceback.format_exc())
