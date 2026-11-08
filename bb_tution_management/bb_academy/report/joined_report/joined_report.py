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
		{"fieldname": "student", "label": "Student ID", "fieldtype": "Link", "options": "Student", "width": 180},
		{"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 220},
		{"fieldname": "admission_date", "label": "Joined Date", "fieldtype": "Date", "width": 120},
		{"fieldname": "gender", "label": "Gender", "fieldtype": "Data", "width": 100},
		{"fieldname": "standard", "label": "Standard", "fieldtype": "Link", "options": "Standard", "width": 140},
		{"fieldname": "current_batch", "label": "Batch", "fieldtype": "Link", "options": "Batch", "width": 160},
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 110},
		{"fieldname": "father_mobile_number", "label": "Father Mobile", "fieldtype": "Data", "width": 130},
		{"fieldname": "mother_mobile_number", "label": "Mother Mobile", "fieldtype": "Data", "width": 130},
	]

def get_data(filters):
	if not filters:
		filters = {}

	conditions = []
	values = {}

	month = MONTHS.get(filters.get("month"))
	if month:
		conditions.append("MONTH(admission_date) = %(month)s")
		values["month"] = month

	if filters.get("year"):
		conditions.append("YEAR(admission_date) = %(year)s")
		values["year"] = filters.get("year")

	if filters.get("gender"):
		conditions.append("gender = %(gender)s")
		values["gender"] = filters.get("gender")

	if filters.get("standard"):
		conditions.append("standard = %(standard)s")
		values["standard"] = filters.get("standard")

	if filters.get("current_batch"):
		conditions.append("current_batch = %(current_batch)s")
		values["current_batch"] = filters.get("current_batch")

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	sql = f"""
		SELECT
			name as student,
			student_name,
			admission_date,
			gender,
			standard,
			current_batch,
			status,
			father_mobile_number,
			mother_mobile_number
		FROM
			`tabStudent`
		WHERE
			admission_date IS NOT NULL AND {where_clause}
		ORDER BY
			admission_date, name
	"""

	return frappe.db.sql(sql, values, as_dict=True)
