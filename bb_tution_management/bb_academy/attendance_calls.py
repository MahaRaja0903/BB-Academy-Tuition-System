"""Attendance Call Works: the students whose parents are owed a call about
attendance this month.

Every Absent or Late day in the calendar month counts, and the count only
grows until the month ends -- the 1st starts everyone again at zero. The count
puts the student in a priority:

    3 - 5     Normal
    6 - 9     Important
    10 +      High Priority

A call covers the priority the student was in when it was made. They leave the
list, and come back only when the count climbs into the next priority: called
at 4 days, listed again at 6 as Important, and again at 10 as High Priority.
A priority the count went past with no call (4 days uncalled, now 7) is tagged
as a missed call on the card.

What the call covered is not stored as a priority: each call pins the
attendance rows it told the parents about (Parent Call Log Item, category
"Attendance"), and the priority already called is the one those pinned rows
reach. So a row re-marked Present simply drops out of both counts.
"""

import json

import frappe
from frappe.utils import add_months, get_datetime, getdate, now_datetime, today

from bb_tution_management.bb_academy.pending_calls import (
	DOCTYPE,
	PRIORITIES,
	_guard,
	_phones,
	_resolve_month,
	missed_calls,
	priority_level,
)
from bb_tution_management.bb_academy.pending_calls import priority_label as _priority_label

ATTENDANCE_DOCTYPE = "Student Attendance"
CATEGORY = "Attendance"
STATUSES = ["Absent", "Late"]

def _month_rows(first_day, student=None, standard=None, batch=None, gender=None):
	"""Every Absent / Late row of Active students in the month, oldest first,
	each flagged with whether a call has already covered it."""
	values = {
		"first_day": first_day,
		"next_month": add_months(first_day, 1),
		"statuses": tuple(STATUSES),
		"attendance": ATTENDANCE_DOCTYPE,
	}
	conditions = ["s.status = 'Active'"]
	for field, column, value in (
		("student", "s.name", student),
		("standard", "s.standard", standard),
		("batch", "s.current_batch", batch),
		("gender", "s.gender", gender),
	):
		if value:
			conditions.append(f"{column} = %({field})s")
			values[field] = value

	return frappe.db.sql(
		f"""
		SELECT a.name AS reference_name, a.student, a.attendance_date AS date,
			a.status, a.remarks,
			EXISTS (
				SELECT 1 FROM `tabParent Call Log Item` i
				WHERE i.reference_name = a.name AND i.reference_doctype = %(attendance)s
			) AS called
		FROM `tabStudent Attendance` a
		INNER JOIN `tabStudent` s ON s.name = a.student
		WHERE {" AND ".join(conditions)}
			AND a.docstatus < 2
			AND a.attendance_date >= %(first_day)s
			AND a.attendance_date < %(next_month)s
			AND a.status IN %(statuses)s
		ORDER BY a.attendance_date, a.name
		""",
		values,
		as_dict=True,
	)


def _this_month():
	return _resolve_month(None)


@frappe.whitelist()
def get_pending_calls(standard=None, batch=None, gender=None):
	"""Students whose month count has reached a priority no call has covered."""
	_guard("read")

	first_day = _this_month()
	by_student = {}
	for row in _month_rows(first_day, standard=standard, batch=batch, gender=gender):
		by_student.setdefault(row.student, []).append(row)

	pending = {}
	for student, rows in by_student.items():
		level = priority_level(len(rows))
		called_level = priority_level(sum(1 for r in rows if r.called))
		if level > called_level:
			pending[student] = (rows, level, called_level)

	result = {
		"records": [],
		"month": first_day,
		"priorities": [{"from": start, "label": label} for start, label in PRIORITIES],
	}
	if not pending:
		return result

	students = {
		s.name: s
		for s in frappe.get_all(
			"Student",
			filters={"name": ["in", list(pending)]},
			fields=[
				"name",
				"student_name",
				"standard",
				"current_batch",
				"gender",
				"image",
				"father_name",
				"mother_name",
				"guardian_name",
				"father_mobile_number",
				"mother_mobile_number",
				"guardian_mobile_number",
				"preferred_mobile_number",
			],
		)
	}

	last_calls = {}
	for call in frappe.db.sql(
		"""
		SELECT c.student, c.called_on, c.called_by, c.spoken_to
		FROM `tabParent Call Log` c
		WHERE c.student IN %(students)s
			AND EXISTS (
				SELECT 1 FROM `tabParent Call Log Item` i
				WHERE i.parent = c.name AND i.parenttype = %(doctype)s AND i.category = %(category)s
			)
		ORDER BY c.called_on DESC
		""",
		{"students": tuple(pending), "doctype": DOCTYPE, "category": CATEGORY},
		as_dict=True,
	):
		last_calls.setdefault(call.student, call)

	records = []
	for student_id, (rows, level, called_level) in pending.items():
		student = students.get(student_id)
		if not student:
			continue

		# The day the count entered its current priority.
		due_since = getdate(rows[PRIORITIES[level - 1][0] - 1].date)
		records.append(
			{
				"student": student_id,
				"student_name": student.student_name,
				"standard": student.standard,
				"batch": student.current_batch,
				"gender": student.gender,
				"image": student.image,
				"father_name": student.father_name,
				"mother_name": student.mother_name,
				"guardian_name": student.guardian_name,
				"phones": _phones(student),
				"count": len(rows),
				"absent": sum(1 for r in rows if r.status == "Absent"),
				"late": sum(1 for r in rows if r.status == "Late"),
				"level": level,
				"priority": _priority_label(level),
				"called_priority": _priority_label(called_level),
				"missed": missed_calls(level, called_level),
				"due_since": due_since,
				"days_pending": (getdate(today()) - due_since).days,
				"last_call": last_calls.get(student_id),
			}
		)

	# Highest priority first, then the longest-waiting family.
	records.sort(key=lambda r: (-r["level"], r["due_since"], -r["count"], r["student_name"] or ""))
	result["records"] = records
	return result


@frappe.whitelist()
def get_student_days(student):
	"""The month's Absent / Late days behind one student's count, newest first."""
	_guard("read")

	rows = _month_rows(_this_month(), student=student)
	rows.reverse()
	return {"days": rows}


@frappe.whitelist()
def log_call(student, spoken_to=None, spoken_to_name=None, called_on=None, called_by=None, call_notes=None):
	"""Record the call home. Every Absent / Late day of the month not yet
	covered is pinned to it, so the student stays off the list until the count
	reaches the next priority.

	The days are read here, not sent by the browser: the call covers what was on
	file when it was logged.
	"""
	_guard("create")

	if not spoken_to:
		frappe.throw(frappe._("Say whom you spoke to."))
	if not called_by:
		frappe.throw(frappe._("Say who made the call."))
	if not (call_notes or "").strip():
		frappe.throw(frappe._("Write down what was spoken."))

	rows = [r for r in _month_rows(_this_month(), student=student) if not r.called]
	if not rows:
		frappe.throw(frappe._("There are no Absent or Late days this month left to inform."))

	doc = frappe.new_doc(DOCTYPE)
	doc.student = student
	doc.spoken_to = spoken_to
	doc.spoken_to_name = spoken_to_name
	doc.called_on = get_datetime(called_on) if called_on else now_datetime()
	doc.called_by = called_by
	doc.call_notes = call_notes
	for row in rows:
		doc.append(
			"mistakes",
			{
				"category": CATEGORY,
				"mistake_date": row.date,
				"result": row.status,
				"details": (row.remarks or "")[:140],
				"reference_doctype": ATTENDANCE_DOCTYPE,
				"reference_name": row.reference_name,
			},
		)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "days": len(rows)}


@frappe.whitelist()
def get_call_history(month=None, standard=None, batch=None, gender=None):
	"""Attendance calls made in one month, newest first, each with the
	priority the student had reached when it was made."""
	_guard("read")

	first_day = _resolve_month(month)
	values = {
		"first_day": first_day,
		"next_month": add_months(first_day, 1),
		"doctype": DOCTYPE,
		"category": CATEGORY,
	}
	conditions = ["c.called_on >= %(first_day)s", "c.called_on < %(next_month)s"]
	for field, column, value in (
		("standard", "c.standard", standard),
		("batch", "c.batch", batch),
		("gender", "s.gender", gender),
	):
		if value:
			conditions.append(f"{column} = %({field})s")
			values[field] = value

	calls = frappe.db.sql(
		f"""
		SELECT c.name, c.student, c.student_name, c.standard, c.batch, s.gender, s.image,
			c.called_on, c.called_by, c.spoken_to, c.spoken_to_name, c.call_notes,
			SUM(i.result = 'Absent') AS absent,
			SUM(i.result = 'Late') AS late,
			MIN(i.mistake_date) AS first_day
		FROM `tabParent Call Log` c
		INNER JOIN `tabParent Call Log Item` i
			ON i.parent = c.name AND i.parenttype = %(doctype)s AND i.category = %(category)s
		LEFT JOIN `tabStudent` s ON s.name = c.student
		WHERE {" AND ".join(conditions)}
		GROUP BY c.name
		ORDER BY c.called_on DESC
		""",
		values,
		as_dict=True,
	)

	for call in calls:
		# Days this call and every earlier attendance call covered in the same
		# month: the count the student had reached when the call was made.
		month_start = _resolve_month(call.first_day)
		reached = frappe.db.sql(
			"""
			SELECT COUNT(i.name)
			FROM `tabParent Call Log Item` i
			INNER JOIN `tabParent Call Log` c ON c.name = i.parent
			WHERE i.parenttype = %(doctype)s AND i.category = %(category)s
				AND c.student = %(student)s AND c.called_on <= %(called_on)s
				AND i.mistake_date >= %(month_start)s AND i.mistake_date < %(next_month)s
			""",
			{
				"doctype": DOCTYPE,
				"category": CATEGORY,
				"student": call.student,
				"called_on": call.called_on,
				"month_start": month_start,
				"next_month": add_months(month_start, 1),
			},
		)[0][0]
		call["count"] = reached
		call["priority"] = _priority_label(priority_level(reached))

	return {"calls": calls}
