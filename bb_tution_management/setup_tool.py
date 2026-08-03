import frappe

def create():
	if frappe.db.exists("DocType", "Bulk Fee Invoice Tool"):
		print("Already exists")
		return
	doc = frappe.get_doc({
		"doctype": "DocType",
		"name": "Bulk Fee Invoice Tool",
		"module": "BB Academy",
		"custom": 0,
		"issingle": 1,
		"fields": [
			{"fieldname": "academic_year", "fieldtype": "Link", "label": "Academic Year", "options": "Academic Year", "reqd": 1},
			{"fieldname": "fee_month", "fieldtype": "Select", "label": "Fee Month", "options": "January\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember", "reqd": 1}
		],
		"permissions": [{"role": "System Manager", "read": 1, "write": 1}]
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	print("Created DocType")
