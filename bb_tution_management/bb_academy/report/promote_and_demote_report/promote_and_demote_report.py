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
		# {"label": _("Approved By"), "fieldname": "approved_by", "fieldtype": "Link", "options": "User", "width": 120},
	]

def get_data(filters):
	filters = filters or {}
	conditions = ["sbt.docstatus < 2"]
	values = {}

	if filters.get("from_date"):
		conditions.append("sbt.effective_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")
	if filters.get("to_date"):
		conditions.append("sbt.effective_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")
	if filters.get("status"):
		conditions.append("sbt.status = %(status)s")
		values["status"] = filters.get("status")
	if filters.get("student"):
		conditions.append("sbt.student = %(student)s")
		values["student"] = filters.get("student")

	where_clause = " AND ".join(conditions)

	data = frappe.db.sql(f"""
		SELECT
			sbt.student,
			stu.student_name,
			stu.standard,
			sbt.previous_batch,
			sbt.new_batch,
			sbt.status,
			sbt.effective_date,
			sbt.reason
		FROM
			`tabStudent Batch Transition` sbt
		JOIN
			`tabStudent` stu ON stu.name = sbt.student
		WHERE
			{where_clause}
		ORDER BY
			sbt.effective_date DESC
	""", values, as_dict=1)

	return data
