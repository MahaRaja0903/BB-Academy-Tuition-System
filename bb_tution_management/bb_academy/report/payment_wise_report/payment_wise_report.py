# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{"label": _("Payment ID"), "fieldname": "name", "fieldtype": "Link", "options": "Fees Payment Entry", "width": 120},
		{"label": _("Student"), "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 150},
		{"label": _("Student Name"), "fieldname": "student_name", "fieldtype": "Data", "width": 150},
		{"label": _("Gender"), "fieldname": "gender", "fieldtype": "Data", "width": 100},
		{"label": _("Payment Date"), "fieldname": "payment_date", "fieldtype": "Date", "width": 120},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Payment Mode"), "fieldname": "payment_mode", "fieldtype": "Data", "width": 120},
		{"label": _("Reference No"), "fieldname": "reference_no", "fieldtype": "Data", "width": 120},
		{"label": _("Fee Invoice"), "fieldname": "fee_invoice", "fieldtype": "Link", "options": "Fee Invoice", "width": 150},
	]

def get_data(filters):
	conditions = []
	if filters:
		if filters.get("from_date"):
			conditions.append(f"pe.payment_date >= '{filters.get('from_date')}'")
		if filters.get("to_date"):
			conditions.append(f"pe.payment_date <= '{filters.get('to_date')}'")
		if filters.get("gender"):
			conditions.append(f"stu.gender = '{filters.get('gender')}'")

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	data = frappe.db.sql(f"""
		SELECT
			pe.name,
			pe.student,
			stu.student_name,
			stu.gender,
			pe.payment_date,
			pe.amount,
			pe.payment_mode,
			pe.reference_no,
			pe.fee_invoice
		FROM
			`tabFees Payment Entry` pe
		JOIN
			`tabStudent` stu ON stu.name = pe.student
		WHERE
			pe.docstatus = 1 AND {where_clause}
		ORDER BY
			pe.payment_date DESC
	""", as_dict=1)

	return data
