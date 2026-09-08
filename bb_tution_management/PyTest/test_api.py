import frappe
from werkzeug.wrappers import Response

@frappe.whitelist(allow_guest=True)
def sw():
    js = "console.log('SW loaded');"
    frappe.response['type'] = 'http'
    frappe.local.response = frappe.request.response # Not sure
    return frappe.Response(js, mimetype="application/javascript", headers={"Service-Worker-Allowed": "/"})
