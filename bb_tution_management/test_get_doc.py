import frappe
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    try:
        frappe.get_doc("BB SMS Settings", "BB SMS Settings")
    except Exception as e:
        print(f"Exception Type: {type(e)}")
        print(f"Exception Message: {str(e)}")
