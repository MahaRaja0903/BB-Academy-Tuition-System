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
		{"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 250},
		{"fieldname": "date_of_birth", "label": "Date of Birth", "fieldtype": "Date", "width": 220},
		{"fieldname": "gender", "label": "Gender", "fieldtype": "Data", "width": 150},
		{"fieldname": "standard", "label": "Standard", "fieldtype": "Link", "options": "Standard", "width": 180},
		{"fieldname": "current_batch", "label": "Batch", "fieldtype": "Link", "options": "Batch", "width": 180},
		# {"fieldname": "parent_mobile", "label": "Parent Mobile", "fieldtype": "Data", "width": 120},
	]

def get_data(filters):
	if not filters:
		filters = {}
		
	conditions = []
	values = {}
	
	if filters.get("month"):
		months = {
			"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
			"July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
		}
		month = months.get(filters.get("month"))
		if month:
			conditions.append("MONTH(date_of_birth) = %(month)s")
			values["month"] = month
			
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
			date_of_birth,
			gender,
			standard,
			current_batch
		FROM
			`tabStudent`
		WHERE
			date_of_birth IS NOT NULL AND {where_clause}
		ORDER BY
			MONTH(date_of_birth), DAY(date_of_birth)
	"""
	
	return frappe.db.sql(sql, values, as_dict=True)
