# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

"""One row per student for a month, pivoted across the performance categories.

Leaving the Category filter blank puts Study, Test, Maths Test and Behaviour
side by side, which is the view a monthly parent/staff review wants. Picking one
category narrows the columns to just that category's grades.
"""

import frappe
from frappe.utils import cint, flt, get_first_day, get_last_day, getdate, today

from bb_tution_management.bb_academy.performance_config import CATEGORIES

# category -> (result -> the column it feeds)
RESULT_COLUMNS = {
	"Study": {
		"Excellent": "study_excellent",
		"Completed": "study_completed",
		"Incomplete": "study_incomplete",
	},
	"Test": {
		"Full Mark": "test_full",
		"Pass Mark": "test_pass",
		"Fail": "test_fail",
	},
	"Maths Test": {
		"Full Mark": "maths_full",
		"Pass Mark": "maths_pass",
		"Fail": "maths_fail",
	},
	"Behaviour": {
		"Good": "behaviour_good",
		"Bad": "behaviour_bad",
		"Worst": "behaviour_worst",
	},
}

CATEGORY_COLUMNS = {
	"Study": [
		{"fieldname": "study_days", "label": "Study Days", "fieldtype": "Int", "width": 95},
		{"fieldname": "study_excellent", "label": "Excellent", "fieldtype": "Int", "width": 90},
		{"fieldname": "study_completed", "label": "Completed", "fieldtype": "Int", "width": 95},
		{"fieldname": "study_incomplete", "label": "Incomplete", "fieldtype": "Int", "width": 100},
	],
	"Test": [
		{"fieldname": "test_days", "label": "Tests", "fieldtype": "Int", "width": 75},
		{"fieldname": "test_full", "label": "Full Mark", "fieldtype": "Int", "width": 95},
		{"fieldname": "test_pass", "label": "Pass Mark", "fieldtype": "Int", "width": 95},
		{"fieldname": "test_fail", "label": "Fail", "fieldtype": "Int", "width": 70},
		{"fieldname": "test_score", "label": "Test Score", "fieldtype": "Data", "width": 110},
		{"fieldname": "test_pct", "label": "Test %", "fieldtype": "Percent", "width": 90},
	],
	"Maths Test": [
		{"fieldname": "maths_days", "label": "Maths Tests", "fieldtype": "Int", "width": 100},
		{"fieldname": "maths_full", "label": "Full Mark", "fieldtype": "Int", "width": 95},
		{"fieldname": "maths_pass", "label": "Pass Mark", "fieldtype": "Int", "width": 95},
		{"fieldname": "maths_fail", "label": "Fail", "fieldtype": "Int", "width": 70},
		{"fieldname": "maths_score", "label": "Maths Score", "fieldtype": "Data", "width": 115},
		{"fieldname": "maths_pct", "label": "Maths %", "fieldtype": "Percent", "width": 95},
	],
	"Behaviour": [
		{"fieldname": "behaviour_days", "label": "Behaviour Days", "fieldtype": "Int", "width": 115},
		{"fieldname": "behaviour_good", "label": "Good", "fieldtype": "Int", "width": 75},
		{"fieldname": "behaviour_bad", "label": "Bad", "fieldtype": "Int", "width": 70},
		{"fieldname": "behaviour_worst", "label": "Worst", "fieldtype": "Int", "width": 75},
		{"fieldname": "behaviour_notes", "label": "What They Did", "fieldtype": "Data", "width": 300},
	],
}

MARKS_CATEGORIES = {"Test": ("test", "test_pct"), "Maths Test": ("maths", "maths_pct")}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_apply_default_dates(filters)

	categories = [filters.category] if filters.category else list(CATEGORIES)
	columns = _get_columns(categories)
	data = _get_data(filters, categories)

	return columns, data


def _apply_default_dates(filters):
	"""Run straight from a workspace link (no filters) and you still get a month."""
	if not filters.get("from_date") or not filters.get("to_date"):
		anchor = getdate(filters.get("from_date") or filters.get("to_date") or today())
		filters.from_date = filters.get("from_date") or get_first_day(anchor)
		filters.to_date = filters.get("to_date") or get_last_day(anchor)

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw("From Date cannot be after To Date")


def _get_columns(categories):
	columns = [
		{
			"fieldname": "student",
			"label": "Student ID",
			"fieldtype": "Link",
			"options": "Student",
			"width": 130,
		},
		{"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 200},
		{
			"fieldname": "standard",
			"label": "Standard",
			"fieldtype": "Link",
			"options": "Standard",
			"width": 100,
		},
		{"fieldname": "batch", "label": "Batch", "fieldtype": "Link", "options": "Batch", "width": 100},
		{"fieldname": "gender", "label": "Gender", "fieldtype": "Data", "width": 80},
	]

	for category in categories:
		columns.extend(CATEGORY_COLUMNS[category])

	# A single "how much went wrong this month" number to sort the list by.
	columns.append(
		{"fieldname": "concern_count", "label": "Concerns", "fieldtype": "Int", "width": 90}
	)
	return columns


def _conditions(filters):
	conditions = ["p.date BETWEEN %(from_date)s AND %(to_date)s"]
	if filters.get("standard"):
		conditions.append("p.standard = %(standard)s")
	if filters.get("batch"):
		conditions.append("p.batch = %(batch)s")
	if filters.get("gender"):
		conditions.append("s.gender = %(gender)s")
	if filters.get("student"):
		conditions.append("p.student = %(student)s")
	if filters.get("category"):
		conditions.append("p.category = %(category)s")
	return " AND ".join(conditions)


def _blank_row(key, categories):
	row = frappe._dict(
		student=key[0],
		student_name=key[1],
		standard=key[2],
		batch=key[3],
		gender=key[4],
		concern_count=0,
	)
	for category in categories:
		for column in CATEGORY_COLUMNS[category]:
			field = column["fieldname"]
			row[field] = "" if column["fieldtype"] == "Data" else 0
	# Running totals for the marks percentages; dropped before the row is returned.
	row._marks = {"test": [0.0, 0.0], "maths": [0.0, 0.0]}
	return row


def _get_data(filters, categories):
	aggregates = frappe.db.sql(
		f"""
		SELECT
			p.student, p.student_name, p.standard, p.batch, s.gender,
			p.category, p.result,
			COUNT(p.name) AS entries,
			SUM(IFNULL(p.marks_obtained, 0)) AS marks_obtained,
			SUM(IFNULL(p.total_marks, 0)) AS total_marks
		FROM `tabStudent Performance Tracker` p
		INNER JOIN `tabStudent` s ON s.name = p.student
		WHERE {_conditions(filters)}
		GROUP BY p.student, p.student_name, p.standard, p.batch, s.gender, p.category, p.result
		""",
		filters,
		as_dict=True,
	)

	rows = {}
	for entry in aggregates:
		if entry.category not in RESULT_COLUMNS:
			# A row left behind by an older schema — skip rather than crash.
			continue
		if entry.category not in categories:
			continue

		key = (entry.student, entry.student_name, entry.standard, entry.batch, entry.gender)
		row = rows.setdefault(key, _blank_row(key, categories))

		count = cint(entry.entries)
		row[f"{_prefix(entry.category)}_days"] += count

		column = RESULT_COLUMNS[entry.category].get(entry.result)
		if column:
			row[column] += count
		if entry.result in ("Incomplete", "Fail", "Bad", "Worst"):
			row.concern_count += count

		if entry.category in MARKS_CATEGORIES:
			bucket = MARKS_CATEGORIES[entry.category][0]
			row._marks[bucket][0] += flt(entry.marks_obtained)
			row._marks[bucket][1] += flt(entry.total_marks)

	if "Behaviour" in categories:
		_attach_behaviour_notes(filters, rows)

	data = []
	for row in rows.values():
		for category, (bucket, pct_field) in MARKS_CATEGORIES.items():
			if category not in categories:
				continue
			scored, total = row._marks[bucket]
			row[f"{bucket}_score"] = f"{scored:g} / {total:g}" if total else ""
			row[pct_field] = round((scored / total) * 100, 2) if total else 0
		row.pop("_marks", None)
		data.append(row)

	# Worst month first — that is the list a monthly review actually works from.
	data.sort(key=lambda r: (-r.concern_count, r.student_name or ""))
	return data


def _prefix(category):
	return {"Study": "study", "Test": "test", "Maths Test": "maths", "Behaviour": "behaviour"}[category]


def _attach_behaviour_notes(filters, rows):
	"""Roll each student's Bad/Worst reasons into one readable cell."""
	if not rows:
		return

	reason_rows = frappe.db.sql(
		f"""
		SELECT p.student, i.behaviour_reason, COUNT(i.name) AS times
		FROM `tabStudent Performance Tracker` p
		INNER JOIN `tabStudent` s ON s.name = p.student
		INNER JOIN `tabStudent Behaviour Reason Item` i
			ON i.parent = p.name AND i.parenttype = 'Student Performance Tracker'
		WHERE {_conditions(filters)} AND p.category = 'Behaviour'
		GROUP BY p.student, i.behaviour_reason
		ORDER BY times DESC, i.behaviour_reason ASC
		""",
		filters,
		as_dict=True,
	)

	notes = {}
	for row in reason_rows:
		label = row.behaviour_reason if cint(row.times) == 1 else f"{row.behaviour_reason} ({row.times})"
		notes.setdefault(row.student, []).append(label)

	for key, row in rows.items():
		row.behaviour_notes = ", ".join(notes.get(key[0], []))
