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
		{"label": _("Admission Number"), "fieldname": "admission_number", "fieldtype": "Link", "options": "Student", "width": 150},
		{"label": _("Student Name"), "fieldname": "student_name", "fieldtype": "Data", "width": 150},
		{"label": _("Standard"), "fieldname": "standard", "fieldtype": "Link", "options": "Standard", "width": 100},
		{"label": _("Batch"), "fieldname": "current_batch", "fieldtype": "Link", "options": "Batch", "width": 100},
		{"label": _("Academic Year"), "fieldname": "academic_year", "fieldtype": "Link", "options": "Academic Year", "width": 120},
		{"label": _("Gender"), "fieldname": "gender", "fieldtype": "Data", "width": 100},
		{"label": _("Date of Birth"), "fieldname": "date_of_birth", "fieldtype": "Date", "width": 120},
		{"label": _("Parent Mobile"), "fieldname": "parent_mobile", "fieldtype": "Data", "width": 120},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
	]

def get_data(filters):
	conditions = []
	if filters:
		if filters.get("standard"):
			conditions.append(f"standard = '{filters.get('standard')}'")
		if filters.get("current_batch"):
			conditions.append(f"current_batch = '{filters.get('current_batch')}'")
		if filters.get("academic_year"):
			conditions.append(f"academic_year = '{filters.get('academic_year')}'")
		if filters.get("status"):
			conditions.append(f"status = '{filters.get('status')}'")
		if filters.get("gender"):
			conditions.append(f"gender = '{filters.get('gender')}'")

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	data = frappe.db.sql(f"""
		SELECT
			name as admission_number,
			student_name,
			standard,
			current_batch,
			academic_year,
			gender,
			date_of_birth,
			parent_mobile,
			status
		FROM
			`tabStudent`
		WHERE
			{where_clause}
		ORDER BY
			creation DESC
	""", as_dict=1)

	return data
