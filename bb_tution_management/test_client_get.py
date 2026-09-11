import frappe
from frappe.client import get
import traceback

def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        get("BB SMS Settings", "BB SMS Settings")
    except Exception as e:
        print(f"Exception Type: {type(e)}")
        print(f"Exception Message: {str(e)}")
