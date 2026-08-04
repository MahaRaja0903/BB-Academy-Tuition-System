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
		{"label": _("Student"), "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 150},
		{"label": _("Student Name"), "fieldname": "student_name", "fieldtype": "Data", "width": 150},
		{"label": _("Standard"), "fieldname": "standard", "fieldtype": "Link", "options": "Standard", "width": 120},
		{"label": _("Previous Batch"), "fieldname": "previous_batch", "fieldtype": "Link", "options": "Batch", "width": 120},
		{"label": _("New Batch"), "fieldname": "new_batch", "fieldtype": "Link", "options": "Batch", "width": 120},
		{"label": _("Status (Promotion/Demotion)"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("Date"), "fieldname": "effective_date", "fieldtype": "Date", "width": 120},
		{"label": _("Reason (Performance)"), "fieldname": "reason", "fieldtype": "Data", "width": 200},
		{"label": _("Approved By"), "fieldname": "approved_by", "fieldtype": "Link", "options": "User", "width": 120},
	]

def get_data(filters):
	conditions = []
	if filters:
		if filters.get("from_date"):
			conditions.append(f"sbh.effective_date >= '{filters.get('from_date')}'")
		if filters.get("to_date"):
			conditions.append(f"sbh.effective_date <= '{filters.get('to_date')}'")
		if filters.get("status"):
			conditions.append(f"sbh.status = '{filters.get('status')}'")
		if filters.get("student"):
			conditions.append(f"sbh.student = '{filters.get('student')}'")

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	data = frappe.db.sql(f"""
		SELECT
			sbh.student,
			stu.student_name,
			stu.standard,
			sbh.previous_batch,
			sbh.new_batch,
			sbh.status,
			sbh.effective_date,
			sbh.reason,
			sbh.approved_by
		FROM
			`tabStudent Batch History` sbh
		JOIN
			`tabStudent` stu ON stu.name = sbh.student
		WHERE
			{where_clause}
		ORDER BY
			sbh.effective_date DESC
	""", as_dict=1)

	return data
