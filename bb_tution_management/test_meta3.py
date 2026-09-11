import frappe
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    try:
        meta = frappe.get_meta("BB SMS Settings")
        print("META EXISTS!")
        print(meta.name)
        print(meta.module)
    except Exception as e:
        print(f"Exception Type: {type(e)}")
        print(f"Exception Message: {str(e)}")
