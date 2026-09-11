import frappe
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    meta = frappe.get_meta("Fee Invoice")
    for table_field in meta.get_table_fields():
        print("TABLE FIELD:", table_field.fieldname, "OPTIONS:", table_field.options)
