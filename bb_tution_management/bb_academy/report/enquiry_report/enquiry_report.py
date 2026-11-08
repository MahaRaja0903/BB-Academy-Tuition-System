# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe

MONTHS = {
	"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
	"July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{"fieldname": "enquiry", "label": "Enquiry ID", "fieldtype": "Link", "options": "Student Enquiry Form", "width": 180},
		{"fieldname": "enquiry_date", "label": "Enquiry Date", "fieldtype": "Date", "width": 120},
		{"fieldname": "applicant_name", "label": "Applicant Name", "fieldtype": "Data", "width": 220},
		{"fieldname": "gender", "label": "Gender", "fieldtype": "Data", "width": 100},
		{"fieldname": "standard", "label": "Standard", "fieldtype": "Link", "options": "Standard", "width": 140},
		{"fieldname": "batch", "label": "Batch", "fieldtype": "Link", "options": "Batch", "width": 160},
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 110},
		{"fieldname": "source", "label": "Source", "fieldtype": "Data", "width": 120},
		{"fieldname": "father_number", "label": "Father Number", "fieldtype": "Data", "width": 130},
		{"fieldname": "mother_number", "label": "Mother Number", "fieldtype": "Data", "width": 130},
		{"fieldname": "next_follow_up_date", "label": "Next Follow-up", "fieldtype": "Date", "width": 120},
	]

def get_data(filters):
	if not filters:
		filters = {}

	conditions = []
	values = {}

	month = MONTHS.get(filters.get("month"))
	if month:
		conditions.append("MONTH(enquiry_date) = %(month)s")
		values["month"] = month

	if filters.get("year"):
		conditions.append("YEAR(enquiry_date) = %(year)s")
		values["year"] = filters.get("year")

	if filters.get("gender"):
		conditions.append("gender = %(gender)s")
		values["gender"] = filters.get("gender")

	if filters.get("standard"):
		conditions.append("standard = %(standard)s")
		values["standard"] = filters.get("standard")

	if filters.get("current_batch"):
		conditions.append("fee_preview_batch = %(current_batch)s")
		values["current_batch"] = filters.get("current_batch")

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	sql = f"""
		SELECT
			name as enquiry,
			enquiry_date,
			applicant_name,
			gender,
			standard,
			fee_preview_batch as batch,
			status,
			source,
			father_number,
			mother_number,
			next_follow_up_date
		FROM
			`tabStudent Enquiry Form`
		WHERE
			enquiry_date IS NOT NULL AND {where_clause}
		ORDER BY
			enquiry_date, name
	"""

	return frappe.db.sql(sql, values, as_dict=True)
