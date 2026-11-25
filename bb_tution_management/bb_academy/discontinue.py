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


# ---------------------------------------------------------------------------
# Discontinued periods (attendance)
# ---------------------------------------------------------------------------
#
# A student owes no attendance from the day they are discontinued until the day
# before they rejoin. Like a Student Holiday those days are derived, here, from
# the Student (still discontinued) and the Student Rejoin Logs (came back), so
# the attendance screen, the previous-day guard, the register and the profile
# all agree on them. An Absent row already marked inside such a period is
# re-tagged with the "Discontinued" attendance status.


def get_discontinued_periods(students=None, from_date=None, to_date=None):
	"""{student: [(start, end), ...]} — inclusive ranges in which each student
	was discontinued. `end` is None while the student is still discontinued.

	`students` narrows the lookup; `from_date`/`to_date` keep only the periods
	overlapping that window.
	"""
	from frappe.utils import add_days

	if students is not None:
		students = list(students)
		if not students:
			return {}

	from_date = getdate(from_date) if from_date else None
	to_date = getdate(to_date) if to_date else None

	student_filters = {"status": "Discontinued", "discontinued__date": ["is", "set"]}
	log_filters = {"discontinued_date": ["is", "set"], "rejoined_date": ["is", "set"]}
	if students is not None:
		student_filters["name"] = ["in", students]
		log_filters["student"] = ["in", students]

	ranges = []
	for s in frappe.get_all("Student", filters=student_filters, fields=["name", "discontinued__date"]):
		ranges.append((s.name, getdate(s.discontinued__date), None))

	for log in frappe.get_all(
		"Student Rejoin Log", filters=log_filters, fields=["student", "discontinued_date", "rejoined_date"]
	):
		end = getdate(add_days(log.rejoined_date, -1))
		start = getdate(log.discontinued_date)
		if end >= start:
			ranges.append((log.student, start, end))

	periods = {}
	for student, start, end in ranges:
		if to_date and start > to_date:
			continue
		if from_date and end and end < from_date:
			continue
		periods.setdefault(student, []).append((start, end))
	for spans in periods.values():
		spans.sort()
	return periods


def is_discontinued_on(periods, student, date):
	"""Was `student` discontinued on `date`, per get_discontinued_periods()?"""
	date = getdate(date)
	return any(start <= date and (end is None or date <= end) for start, end in periods.get(student, ()))


def tag_discontinued_absences(student, start, end=None):
	"""Re-tag the Absent rows marked for `student` while discontinued as
	"Discontinued".

	Staff had to mark a left student Absent to get past the previous-day guard;
	those rows must not count as absences (monthly totals, absence calls,
	attendance %). They are re-tagged rather than deleted because the absence
	WhatsApp already sent links to them. Present/Late rows are real attendance
	and are kept. Returns the number of rows re-tagged.
	"""
	from frappe.utils import now

	conditions = "student = %(student)s AND status = 'Absent' AND attendance_date >= %(start)s"
	if end:
		conditions += " AND attendance_date <= %(end)s"
	frappe.db.sql(
		f"""
		UPDATE `tabStudent Attendance`
		SET status = 'Discontinued', modified = %(modified)s, modified_by = %(user)s
		WHERE {conditions}
		""",
		{
			"student": student,
			"start": getdate(start),
			"end": getdate(end) if end else None,
			"modified": now(),
			"user": frappe.session.user,
		},
	)
	return frappe.db._cursor.rowcount or 0
