# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

"""Which students still have no Study / Test / H.W / Behaviour grade.

A student is owed a grade for a category on every working day the attendance
register marks them Present or Late — the same students the Performance
Manager lists for grading. The day is not owed when it is a holiday for the
student's batch (unless a Special Class Day lifted it), or when the batch's
session for that category was marked "Not Planned".

Test can run several times a day; any one Test grade covers the day here,
since the question this report answers is "was anything entered at all".
"""

import frappe
from frappe.utils import getdate, today

from bb_tution_management.bb_academy.performance_config import PRESENT_STATUSES

# Class is left out: it is not graded, only recorded as attended.
PENDING_CATEGORIES = ["Study", "Test", "H.W", "Behaviour"]

CATEGORY_FIELDS = {
	"Study": "study",
	"Test": "test",
	"H.W": "hw",
	"Behaviour": "behaviour",
}

# Tracking started on 1 October 2026; earlier days were never graded.
DEFAULT_FROM_DATE = "2026-10-01"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.from_date = getdate(filters.get("from_date") or DEFAULT_FROM_DATE)
	filters.to_date = getdate(filters.get("to_date") or today())
	if filters.from_date > filters.to_date:
		frappe.throw("From Date cannot be after To Date")

	categories = [filters.category] if filters.get("category") else list(PENDING_CATEGORIES)
	pending = _get_pending(filters, categories)

	if filters.get("view") == "Date Wise":
		return _date_wise_columns(categories), _date_wise_data(pending, categories)
	return _student_columns(categories), _student_data(pending, categories)


def _student_info_columns():
	return [
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
	]


def _category_columns(categories, fieldtype, width):
	return [
		{
			"fieldname": f"{CATEGORY_FIELDS[c]}_pending",
			"label": f"{c} Pending",
			"fieldtype": fieldtype,
			"width": width,
		}
		for c in categories
	]


def _student_columns(categories):
	return (
		_student_info_columns()
		+ [{"fieldname": "present_days", "label": "Present Days", "fieldtype": "Int", "width": 105}]
		+ _category_columns(categories, "Int", 115)
		+ [
			{"fieldname": "total_pending", "label": "Total Pending", "fieldtype": "Int", "width": 110},
			{"fieldname": "pending_dates", "label": "Pending Dates", "fieldtype": "Data", "width": 320},
		]
	)


def _date_wise_columns(categories):
	return (
		[{"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 100}]
		+ _student_info_columns()
		+ [{"fieldname": "attendance_status", "label": "Attendance", "fieldtype": "Data", "width": 95}]
		+ _category_columns(categories, "Data", 115)
		+ [{"fieldname": "total_pending", "label": "Total Pending", "fieldtype": "Int", "width": 110}]
	)


def _get_pending(filters, categories):
	"""One entry per present student per working day, with the categories still
	missing a grade."""
	conditions = [
		"a.attendance_date BETWEEN %(from_date)s AND %(to_date)s",
		"a.status IN %(present)s",
		"s.status = 'Active'",
	]
	if filters.get("standard"):
		conditions.append("a.standard = %(standard)s")
	if filters.get("batch"):
		conditions.append("a.batch = %(batch)s")
	if filters.get("gender"):
		conditions.append("s.gender = %(gender)s")
	if filters.get("student"):
		conditions.append("a.student = %(student)s")

	params = {**filters, "present": tuple(PRESENT_STATUSES), "categories": tuple(categories)}

	present = frappe.db.sql(
		f"""
		SELECT a.attendance_date AS date, a.student, s.student_name,
			a.standard, a.batch, a.status AS attendance_status
		FROM `tabStudent Attendance` a
		INNER JOIN `tabStudent` s ON s.name = a.student
		WHERE {" AND ".join(conditions)}
		ORDER BY a.attendance_date ASC, a.standard ASC, a.batch ASC,
			TRIM(SUBSTRING_INDEX(s.student_name, '.', -1)) ASC
		""",
		params,
		as_dict=True,
	)
	if not present:
		return []

	graded = {
		(getdate(r.date), r.student, r.category)
		for r in frappe.db.sql(
			"""
			SELECT DISTINCT date, student, category
			FROM `tabStudent Performance Tracker`
			WHERE date BETWEEN %(from_date)s AND %(to_date)s AND category IN %(categories)s
			""",
			params,
			as_dict=True,
		)
	}

	not_planned = {
		(getdate(r.date), r.standard, r.batch, r.category)
		for r in frappe.get_all(
			"Student Performance Session",
			filters={
				"date": ["between", [filters.from_date, filters.to_date]],
				"category": ["in", categories],
				"no_session": 1,
			},
			fields=["date", "standard", "batch", "category"],
		)
	}

	is_holiday = _holiday_checker(filters)

	pending = []
	for row in present:
		date = getdate(row.date)
		if is_holiday(date, row.standard, row.batch):
			continue
		missing = [
			c
			for c in categories
			if (date, row.student, c) not in graded
			and (date, row.standard, row.batch, c) not in not_planned
		]
		row.date = date
		row.missing = missing
		pending.append(row)
	return pending


def _holiday_checker(filters):
	"""Mirror attendance.get_holiday_details for a whole date range at once, so
	the report does not query twice per student per day."""
	date_range = ["between", [filters.from_date, filters.to_date]]
	holidays = frappe.get_all(
		"Attendance Holiday",
		filters={"holiday_date": date_range},
		fields=["holiday_date AS date", "scope", "standard", "batch"],
	)
	special_days = frappe.get_all(
		"Special Class Day",
		filters={"class_date": date_range},
		fields=["class_date AS date", "scope", "standard", "batch"],
	)

	def covers(records, date, standard, batch):
		for r in records:
			if getdate(r.date) != date:
				continue
			if r.scope == "Entire School":
				return True
			if r.scope == "Standard" and r.standard == standard:
				return True
			if r.scope == "Standard + Batch" and r.standard == standard and r.batch == batch:
				return True
		return False

	def is_holiday(date, standard, batch):
		return covers(holidays, date, standard, batch) and not covers(
			special_days, date, standard, batch
		)

	return is_holiday


def _student_data(pending, categories):
	rows = {}
	for entry in pending:
		key = (entry.student, entry.standard, entry.batch)
		row = rows.get(key)
		if not row:
			row = rows[key] = frappe._dict(
				student=entry.student,
				student_name=entry.student_name,
				standard=entry.standard,
				batch=entry.batch,
				present_days=0,
				total_pending=0,
				_dates=[],
			)
			for c in categories:
				row[f"{CATEGORY_FIELDS[c]}_pending"] = 0

		row.present_days += 1
		for c in entry.missing:
			row[f"{CATEGORY_FIELDS[c]}_pending"] += 1
		row.total_pending += len(entry.missing)
		if entry.missing:
			row._dates.append(entry.date.strftime("%d-%m"))

	data = []
	for row in rows.values():
		if not row.total_pending:
			continue
		row.pending_dates = ", ".join(row.pop("_dates"))
		data.append(row)

	# Most behind first — that is the list staff chase up.
	data.sort(key=lambda r: (-r.total_pending, r.standard or "", r.batch or "", r.student_name or ""))
	return data


def _date_wise_data(pending, categories):
	data = []
	for entry in pending:
		if not entry.missing:
			continue
		row = frappe._dict(
			date=entry.date,
			student=entry.student,
			student_name=entry.student_name,
			standard=entry.standard,
			batch=entry.batch,
			attendance_status=entry.attendance_status,
			total_pending=len(entry.missing),
		)
		for c in categories:
			row[f"{CATEGORY_FIELDS[c]}_pending"] = "Pending" if c in entry.missing else ""
		data.append(row)
	return data
