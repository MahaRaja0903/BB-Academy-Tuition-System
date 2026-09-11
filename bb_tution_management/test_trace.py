import frappe
import traceback
from frappe.permissions import check_doctype_permission
from frappe.desk.form.save import savedocs

original_check = frappe.permissions.check_doctype_permission

def my_check(doctype, ptype="read"):
    if doctype == "DocType":
        print("FOUND CHECK DOCTYPE PERMISSION FOR DOCTYPE!")
        print(traceback.format_stack())
    return original_check(doctype, ptype)

frappe.permissions.check_doctype_permission = my_check
import frappe.model.document
frappe.model.document.check_doctype_permission = my_check
import frappe.desk.form.load
frappe.desk.form.load.check_doctype_permission = my_check
import frappe.model.db_query
frappe.model.db_query.check_doctype_permission = my_check
import frappe.client
frappe.client.check_doctype_permission = my_check

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
        print("Exception:", str(e))
