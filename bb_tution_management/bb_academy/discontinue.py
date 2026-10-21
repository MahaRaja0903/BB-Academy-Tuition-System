# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

"""Discontinue records shared by the Month Wise Discontinue and Reason For
Discontinue reports.

A student who rejoins has their discontinue date/reason cleared on the Student
and copied to a Student Rejoin Log, so both sources are read: current
Discontinued students, plus rejoin logs for the ones who came back.
"""

import frappe
from frappe import _
from frappe.utils import cint, getdate

NOT_CATEGORISED = "Not Categorised"


def get_discontinue_records(filters):
	"""One dict per discontinue, filtered by date range, standard, batch and reason."""
	from_date = getdate(filters.get("from_date")) if filters.get("from_date") else None
	to_date = getdate(filters.get("to_date")) if filters.get("to_date") else None

	student_filters = {}
	for key in ("standard", "current_batch"):
		if filters.get(key):
			student_filters[key] = filters.get(key)

	students = {
		s.name: s
		for s in frappe.get_all(
			"Student",
			filters=student_filters,
			fields=["name", "student_name", "standard", "current_batch", "status",
				"discontinued__date", "discontinue_reason_category", "discontinued_reason"],
		)
	}

	records = []
	for s in students.values():
		if s.status == "Discontinued" and s.discontinued__date:
			records.append(make_record(s, s.discontinued__date, s.discontinue_reason_category,
				s.discontinued_reason))

	if cint(filters.get("include_rejoined", 1)):
		logs = frappe.get_all(
			"Student Rejoin Log",
			filters={"discontinued_date": ["is", "set"], "student": ["in", list(students) or [""]]},
			fields=["student", "discontinued_date", "discontinue_reason_category",
				"discontinued_reason", "rejoined_date"],
		)
		for log in logs:
			records.append(make_record(students[log.student], log.discontinued_date,
				log.discontinue_reason_category, log.discontinued_reason, log.rejoined_date))

	reason = filters.get("discontinue_reason_category")
	return sorted(
		(
			r for r in records
			if (not from_date or r["discontinued_date"] >= from_date)
			and (not to_date or r["discontinued_date"] <= to_date)
			and (not reason or r["reason_category"] == reason)
		),
		key=lambda r: (r["discontinued_date"], r["student_name"] or ""),
	)


def make_record(student, discontinued_date, category, remarks, rejoined_date=None):
	return {
		"student": student.name,
		"student_name": student.student_name,
		"standard": student.standard,
		"current_batch": student.current_batch,
		"discontinued_date": getdate(discontinued_date),
		"reason_category": category or NOT_CATEGORISED,
		"remarks": (remarks or "").strip(),
		"rejoined_date": rejoined_date,
		"current_status": _("Rejoined") if rejoined_date else _("Discontinued"),
	}


def student_columns():
	"""Columns for the student rows under each group."""
	return [
		{"fieldname": "student", "label": _("Student ID"), "fieldtype": "Link", "options": "Student", "width": 140},
		{"fieldname": "student_name", "label": _("Student Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "standard", "label": _("Standard"), "fieldtype": "Link", "options": "Standard", "width": 100},
		{"fieldname": "current_batch", "label": _("Batch"), "fieldtype": "Link", "options": "Batch", "width": 90},
		{"fieldname": "discontinued_date", "label": _("Discontinued Date"), "fieldtype": "Date", "width": 130},
		{"fieldname": "current_status", "label": _("Current Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "rejoined_date", "label": _("Rejoined Date"), "fieldtype": "Date", "width": 120},
		{"fieldname": "remarks", "label": _("Remarks"), "fieldtype": "Data", "width": 320},
	]


def report_summary(records):
	rejoined = sum(1 for r in records if r["rejoined_date"])
	return [
		{"label": _("Total Discontinued"), "value": len(records), "indicator": "Red", "datatype": "Int"},
		{"label": _("Still Discontinued"), "value": len(records) - rejoined, "indicator": "Orange", "datatype": "Int"},
		{"label": _("Rejoined"), "value": rejoined, "indicator": "Green", "datatype": "Int"},
	]
