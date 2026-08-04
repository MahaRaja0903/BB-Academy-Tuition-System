# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{"fieldname": "student", "label": "Student ID", "fieldtype": "Link", "options": "Student", "width": 120},
		{"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 150},
		{"fieldname": "standard", "label": "Standard", "fieldtype": "Link", "options": "Standard", "width": 120},
		{"fieldname": "batch", "label": "Batch", "fieldtype": "Link", "options": "Batch", "width": 120},
		{"fieldname": "starting_payment_amount", "label": "Starting Amt", "fieldtype": "Currency", "width": 120},
		{"fieldname": "starting_payment_paid", "label": "Starting Paid", "fieldtype": "Currency", "width": 120},
		{"fieldname": "starting_payment_pending", "label": "Starting Pending", "fieldtype": "Currency", "width": 120},
		{"fieldname": "regular_fee_pending", "label": "Regular Fee Pending", "fieldtype": "Currency", "width": 140},
		{"fieldname": "total_pending", "label": "Total Pending", "fieldtype": "Currency", "width": 120}
	]

def get_data(filters):
	if not filters:
		filters = {}

	conditions = ["s.status = 'Active'"]
	values = {}

	if filters.get("student"):
		conditions.append("s.name = %(student)s")
		values["student"] = filters.get("student")

	if filters.get("standard"):
		conditions.append("s.standard = %(standard)s")
		values["standard"] = filters.get("standard")

	if filters.get("batch"):
		conditions.append("s.current_batch = %(batch)s")
		values["batch"] = filters.get("batch")

	where_clause = " AND ".join(conditions) if conditions else "1=1"
	
	having_clause = ""
	if int(filters.get("show_only_pending", 1)):
		having_clause = "HAVING total_pending > 0"

	sql = f"""
		SELECT
			s.name AS student,
			s.student_name,
			s.standard,
			s.current_batch AS batch,
			
			COALESCE(SUM(CASE WHEN IFNULL(fi.is_starting_fee, 0) = 1 THEN fi.grand_total ELSE 0 END), 0) AS starting_payment_amount,
			COALESCE(SUM(CASE WHEN IFNULL(fi.is_starting_fee, 0) = 1 THEN fi.paid_amount ELSE 0 END), 0) AS starting_payment_paid,
			COALESCE(SUM(CASE WHEN IFNULL(fi.is_starting_fee, 0) = 1 THEN fi.outstanding_amount ELSE 0 END), 0) AS starting_payment_pending,
			
			COALESCE(SUM(CASE WHEN IFNULL(fi.is_starting_fee, 0) = 0 THEN fi.outstanding_amount ELSE 0 END), 0) AS regular_fee_pending,
			
			COALESCE(SUM(fi.outstanding_amount), 0) AS total_pending

		FROM `tabStudent` s
		LEFT JOIN `tabFee Invoice` fi ON s.name = fi.student AND fi.docstatus = 1
		WHERE {where_clause}
		GROUP BY s.name
		{having_clause}
		ORDER BY s.student_name
	"""
	
	return frappe.db.sql(sql, values, as_dict=True)
