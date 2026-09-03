import frappe

def execute():
    doc = frappe.get_doc({
        "doctype": "Street Name",
        "street_name": "Test Street",
        "area": "PORUR"
    })
    doc.insert()
    print("Generated Name:", doc.name)
