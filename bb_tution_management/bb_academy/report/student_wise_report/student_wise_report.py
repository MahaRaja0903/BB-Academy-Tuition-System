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
		{"label": _("Father Mobile Number"), "fieldname": "father_mobile_number", "fieldtype": "Data", "width": 150},
		{"label": _("Mother Mobile Number"), "fieldname": "mother_mobile_number", "fieldtype": "Data", "width": 150},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
	]

def get_data(filters):
	filters = filters or {}
	conditions = []
	values = {}

	for fieldname in ("standard", "current_batch", "academic_year", "status", "gender"):
		if filters.get(fieldname):
			conditions.append(f"`{fieldname}` = %({fieldname})s")
			values[fieldname] = filters.get(fieldname)

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
			father_mobile_number,
			mother_mobile_number,
			status
		FROM
			`tabStudent`
		WHERE
			{where_clause}
		ORDER BY
			creation DESC
	""", values, as_dict=1)

	return data
