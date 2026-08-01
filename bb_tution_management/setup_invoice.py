import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def setup():
	# Create Fee Invoice Item Child Doctype
	if not frappe.db.exists("DocType", "Fee Invoice Item"):
		doc = frappe.get_doc({
			"doctype": "DocType",
			"name": "Fee Invoice Item",
			"module": "BB Academy",
			"custom": 0,
			"istable": 1,
			"fields": [
				{"fieldname": "description", "fieldtype": "Data", "label": "Description", "in_list_view": 1, "reqd": 1},
				{"fieldname": "amount", "fieldtype": "Currency", "label": "Amount", "in_list_view": 1, "reqd": 1}
			]
		})
		doc.insert(ignore_permissions=True)
		print("Created Fee Invoice Item")

	# Add fields to Fee Invoice
	fields = [
		dict(fieldname='is_starting_fee', label='Is Starting Fee', fieldtype='Check', default='0', insert_after='status'),
		dict(fieldname='items', label='Fee Items', fieldtype='Table', options='Fee Invoice Item', insert_after='payment_amounts_section'),
		dict(fieldname='grand_total', label='Grand Total', fieldtype='Currency', read_only=1, insert_after='items')
	]
	
	for df in fields:
		if not frappe.db.exists("Custom Field", {"dt": "Fee Invoice", "fieldname": df['fieldname']}):
			create_custom_field("Fee Invoice", df)
			print(f"Added {df['fieldname']} to Fee Invoice")

	frappe.db.commit()

