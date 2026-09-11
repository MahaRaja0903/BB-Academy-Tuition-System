import frappe
import traceback
from frappe.desk.form.save import savedocs

original_db_get_all = frappe.db.get_all

def my_db_get_all(*args, **kwargs):
    doctype = args[0] if args else kwargs.get("doctype")
    if doctype == "DocType":
        print("FOUND GET_ALL FOR DOCTYPE!")
        print(traceback.format_stack())
    return original_db_get_all(*args, **kwargs)

frappe.db.get_all = my_db_get_all

def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    frappe.set_user("staff@gmail.com")
    
    draft = frappe.get_last_doc("Fee Invoice", filters={"docstatus": 0})
    if not draft: return
    
    doc_dict = draft.as_dict()
    doc_dict["__last_sync_on"] = frappe.utils.now()
    doc_dict["modified"] = doc_dict.get("modified")
    doc_str = frappe.as_json(doc_dict)
    
    try:
        savedocs(doc_str, 'Submit')
    except Exception as e:
        print("EXC", str(e))
