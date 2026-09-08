import frappe
frappe.init(site="admin.dreamtechsolution.com")
frappe.connect()

docs = frappe.get_list("Student Enquiry Form", or_filters=[["father_number", "like", "%123%"], ["mother_number", "like", "%123%"]])
print(docs)
