# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

"""Every call home owed by Pending Call Works and Attendance Call Works: the
calls made, who made them, and the ones missed.

One row is one call owed:

    Called        a call made in the date range, before the count went past
                  a priority with nobody ringing
    Called Late   a call made, but only after the count had already gone
                  past a priority uncalled (e.g. H.W reached 7 before the call,
                  so the call at 3 was missed)
    Pending       owed today and not yet made
    Missed        owed today, and the count has already gone past a priority
                  with no call

Pending Call Works rows are per category (H.W, Test, ...); Attendance Call
Works rows are per student, counting the month's Absent and Late days. Pending
and Missed rows are today's list, so they appear only when the range reaches
today.

The "In-charge" is the staff member who spoke from the tuition.
"""

from collections import defaultdict

import frappe
from frappe.utils import add_days, get_first_day, getdate, today

from bb_tution_management.bb_academy import attendance_calls, pending_calls
from bb_tution_management.bb_academy.pending_calls import (
	PRIORITIES,
	missed_calls,
	priority_label,
	priority_level,
)

PENDING_WORKS = "Pending Call Works"
ATTENDANCE_WORKS = "Attendance Call Works"

CALLED = "Called"
CALLED_LATE = "Called Late"
PENDING = "Pending"
MISSED = "Missed"

# Missed first: the families most overdue for a call.
STATUS_ORDER = {MISSED: 0, PENDING: 1, CALLED_LATE: 2, CALLED: 3}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.from_date = getdate(filters.get("from_date") or get_first_day(today()))
	filters.to_date = getdate(filters.get("to_date") or today())
	if filters.from_date > filters.to_date:
		frappe.throw("From Date cannot be after To Date")

	works = [filters.call_work] if filters.get("call_work") else [PENDING_WORKS, ATTENDANCE_WORKS]

	rows = _called_rows(filters, works)
	if filters.to_date >= getdate(today()) and not filters.get("called_by"):
		rows += _pending_rows(filters, works)

	rows = [r for r in rows if _matches(r, filters)]
	# Owed calls first, Missed before Pending and the longest-waiting first;
	# then the calls made, newest first.
	owed = sorted(
		(r for r in rows if r["status"] in (MISSED, PENDING)),
		key=lambda r: (STATUS_ORDER[r["status"]], -(r["days"] or 0), r["student_name"] or ""),
	)
	made = sorted(
		(r for r in rows if r["status"] in (CALLED, CALLED_LATE)),
		key=lambda r: str(r["called_on"]),
		reverse=True,
	)
	rows = owed + made

	return _columns(), rows, None, _chart(rows), _summary(rows)


def _matches(row, filters):
	if filters.get("status") and row["status"] != filters.status:
		return False
	if filters.get("category") and row["category"] != filters.category:
		return False
	if filters.get("priority") and row.get("priority") != filters.priority:
		return False
	if filters.get("student") and row["student"] != filters.student:
		return False
	if filters.get("called_by") and row.get("called_by") != filters.called_by:
		return False
	return True


def _missed_text(missed):
	return ", ".join(f"{m['from']} ({m['label']})" for m in missed)


# ---------------------------------------------------------------- calls made


def _called_rows(filters, works):
	values = {"from_date": filters.from_date, "to_date": add_days(filters.to_date, 1)}
	conditions = ["c.called_on >= %(from_date)s", "c.called_on < %(to_date)s"]
	for field, column in (
		("standard", "c.standard"),
		("batch", "c.batch"),
		("gender", "s.gender"),
		("student", "c.student"),
		("called_by", "c.called_by"),
	):
		if filters.get(field):
			conditions.append(f"{column} = %({field})s")
			values[field] = filters.get(field)

	calls = frappe.db.sql(
		f"""
		SELECT c.name, c.student, c.student_name, c.standard, c.batch, s.gender,
			c.called_on, c.called_by, c.spoken_to, c.spoken_to_name, c.call_notes,
			s.father_mobile_number, s.mother_mobile_number, s.guardian_mobile_number,
			s.preferred_mobile_number
		FROM `tabParent Call Log` c
		LEFT JOIN `tabStudent` s ON s.name = c.student
		WHERE {" AND ".join(conditions)}
		""",
		values,
		as_dict=True,
	)
	if not calls:
		return []

	items = defaultdict(lambda: defaultdict(list))
	for item in frappe.db.sql(
		"""
		SELECT parent, category, mistake_date, result
		FROM `tabParent Call Log Item`
		WHERE parenttype = %(doctype)s AND parent IN %(parents)s
		ORDER BY mistake_date, idx
		""",
		{"doctype": pending_calls.DOCTYPE, "parents": tuple(c.name for c in calls)},
		as_dict=True,
	):
		items[item.parent][item.category].append(item)

	attendance_reached = (
		_attendance_reached(calls, items) if ATTENDANCE_WORKS in works else {}
	)
	limit = pending_calls.threshold()

	rows = []
	for call in calls:
		base = {
			"student": call.student,
			"student_name": call.student_name,
			"standard": call.standard,
			"batch": call.batch,
			"gender": call.gender,
			"phone": _phone(call),
			"called_on": call.called_on,
			"called_by": call.called_by,
			"spoken_to": call.spoken_to,
			"spoken_to_name": call.spoken_to_name,
			"call_notes": call.call_notes,
			"call_log": call.name,
		}
		for category, category_items in items[call.name].items():
			if category == attendance_calls.CATEGORY:
				if ATTENDANCE_WORKS not in works:
					continue
				reached = attendance_reached[call.name]
				row = _attendance_called_row(base, category_items, reached)
			else:
				if PENDING_WORKS not in works:
					continue
				row = _tracker_called_row(base, category, category_items, limit)
			rows.append(row)
	return rows


def _tracker_called_row(base, category, category_items, limit):
	count = len(category_items)
	level = priority_level(count) if count >= limit else 0
	missed = missed_calls(level, floor=limit) if level else []
	due_since = getdate(category_items[limit - 1].mistake_date) if count >= limit else None
	return {
		**base,
		"status": CALLED_LATE if missed else CALLED,
		"call_work": PENDING_WORKS,
		"category": category,
		"count": count,
		"details": "",
		"priority": priority_label(level),
		"missed": _missed_text(missed),
		"due_since": due_since,
		"days": (getdate(base["called_on"]) - due_since).days if due_since else None,
	}


def _attendance_called_row(base, category_items, reached):
	before, dates = reached
	count = len(dates)
	level = priority_level(count)
	missed = missed_calls(level, priority_level(before))
	due_since = getdate(dates[PRIORITIES[level - 1][0] - 1]) if level else None
	absent = sum(1 for i in category_items if i.result == "Absent")
	late = sum(1 for i in category_items if i.result == "Late")
	return {
		**base,
		"status": CALLED_LATE if missed else CALLED,
		"call_work": ATTENDANCE_WORKS,
		"category": attendance_calls.CATEGORY,
		"count": count,
		"details": f"Absent {absent} · Late {late}",
		"priority": priority_label(level),
		"missed": _missed_text(missed),
		"due_since": due_since,
		"days": (getdate(base["called_on"]) - due_since).days if due_since else None,
	}


def _attendance_reached(calls, items):
	"""For each attendance call: (days the earlier calls that month had
	covered, sorted dates of every day covered up to and including this call).
	The month count when the call was made is the length of the second."""
	attendance_calls_made = [c for c in calls if items[c.name].get(attendance_calls.CATEGORY)]
	if not attendance_calls_made:
		return {}

	earliest = min(
		getdate(items[c.name][attendance_calls.CATEGORY][0].mistake_date) for c in attendance_calls_made
	)
	by_month = defaultdict(list)
	for row in frappe.db.sql(
		"""
		SELECT c.name AS call_log, c.student, c.called_on, i.mistake_date
		FROM `tabParent Call Log Item` i
		INNER JOIN `tabParent Call Log` c ON c.name = i.parent
		WHERE i.parenttype = %(doctype)s AND i.category = %(category)s
			AND c.student IN %(students)s AND i.mistake_date >= %(from_date)s
		ORDER BY c.called_on, c.name
		""",
		{
			"doctype": pending_calls.DOCTYPE,
			"category": attendance_calls.CATEGORY,
			"students": tuple({c.student for c in attendance_calls_made}),
			"from_date": get_first_day(earliest),
		},
		as_dict=True,
	):
		by_month[(row.student, get_first_day(row.mistake_date))].append(row)

	reached = {}
	for rows in by_month.values():
		covered = []
		seen = []
		for row in rows:
			if row.call_log not in seen:
				seen.append(row.call_log)
		for call in seen:
			before = len(covered)
			covered += [getdate(r.mistake_date) for r in rows if r.call_log == call]
			covered.sort()
			reached[call] = (before, list(covered))
	return reached


def _phone(student):
	phones = pending_calls._phones(student)
	return phones[0]["number"] if phones else None


# ---------------------------------------------------------------- owed today


def _pending_rows(filters, works):
	args = {"standard": filters.get("standard"), "batch": filters.get("batch"), "gender": filters.get("gender")}
	rows = []

	if PENDING_WORKS in works:
		for r in pending_calls.get_pending_calls(**args)["records"]:
			for c in r["categories"]:
				if not c["due"]:
					continue
				rows.append(
					{
						**_pending_base(r),
						"status": MISSED if c["missed"] else PENDING,
						"call_work": PENDING_WORKS,
						"category": c["category"],
						"count": c["count"],
						"details": "",
						"priority": c["priority"],
						"missed": _missed_text(c["missed"]),
						"due_since": c["due_since"],
						"days": (getdate(today()) - getdate(c["due_since"])).days,
					}
				)

	if ATTENDANCE_WORKS in works:
		for r in attendance_calls.get_pending_calls(**args)["records"]:
			rows.append(
				{
					**_pending_base(r),
					"status": MISSED if r["missed"] else PENDING,
					"call_work": ATTENDANCE_WORKS,
					"category": attendance_calls.CATEGORY,
					"count": r["count"],
					"details": f"Absent {r['absent']} · Late {r['late']}",
					"priority": r["priority"],
					"missed": _missed_text(r["missed"]),
					"due_since": r["due_since"],
					"days": r["days_pending"],
				}
			)
	return rows


def _pending_base(record):
	last_call = record.get("last_call") or {}
	return {
		"student": record["student"],
		"student_name": record["student_name"],
		"standard": record["standard"],
		"batch": record["batch"],
		"gender": record["gender"],
		"phone": record["phones"][0]["number"] if record["phones"] else None,
		"last_call_on": last_call.get("called_on"),
		"last_called_by": last_call.get("called_by"),
	}


# ---------------------------------------------------------------- output


def _columns():
	return [
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 110},
		{"fieldname": "call_work", "label": "Call Work", "fieldtype": "Data", "width": 160},
		{"fieldname": "category", "label": "Category", "fieldtype": "Data", "width": 100},
		{"fieldname": "student", "label": "Student ID", "fieldtype": "Link", "options": "Student", "width": 130},
		{"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 180},
		{"fieldname": "standard", "label": "Standard", "fieldtype": "Link", "options": "Standard", "width": 100},
		{"fieldname": "batch", "label": "Batch", "fieldtype": "Link", "options": "Batch", "width": 100},
		{"fieldname": "count", "label": "Count", "fieldtype": "Int", "width": 70},
		{"fieldname": "details", "label": "Breakdown", "fieldtype": "Data", "width": 140},
		{"fieldname": "priority", "label": "Priority", "fieldtype": "Data", "width": 110},
		{"fieldname": "missed", "label": "Missed Call At", "fieldtype": "Data", "width": 180},
		{"fieldname": "due_since", "label": "Due Since", "fieldtype": "Date", "width": 100},
		{"fieldname": "days", "label": "Days to Call / Pending", "fieldtype": "Int", "width": 100},
		{"fieldname": "called_on", "label": "Called On", "fieldtype": "Datetime", "width": 150},
		{"fieldname": "called_by", "label": "In-charge (Called By)", "fieldtype": "Link", "options": "Staff", "width": 150},
		{"fieldname": "spoken_to", "label": "Spoken To", "fieldtype": "Data", "width": 90},
		{"fieldname": "spoken_to_name", "label": "Spoken To Name", "fieldtype": "Data", "width": 130},
		{"fieldname": "call_notes", "label": "What Was Spoken", "fieldtype": "Data", "width": 220},
		{"fieldname": "last_call_on", "label": "Last Call", "fieldtype": "Datetime", "width": 150},
		{"fieldname": "last_called_by", "label": "Last Called By", "fieldtype": "Link", "options": "Staff", "width": 130},
		{"fieldname": "phone", "label": "Phone", "fieldtype": "Data", "width": 120},
		{"fieldname": "call_log", "label": "Call Log", "fieldtype": "Link", "options": "Parent Call Log", "width": 130},
	]


def _summary(rows):
	count = defaultdict(int)
	for r in rows:
		count[r["status"]] += 1
	return [
		{"label": "Calls Made", "value": count[CALLED] + count[CALLED_LATE], "indicator": "Green"},
		{"label": "Called Late", "value": count[CALLED_LATE], "indicator": "Orange"},
		{"label": "Pending", "value": count[PENDING], "indicator": "Blue"},
		{"label": "Missed", "value": count[MISSED], "indicator": "Red"},
	]


def _chart(rows):
	"""Calls made by each in-charge, on time and late."""
	on_time = defaultdict(int)
	late = defaultdict(int)
	for r in rows:
		if r["status"] == CALLED:
			on_time[r["called_by"]] += 1
		elif r["status"] == CALLED_LATE:
			late[r["called_by"]] += 1
	staff = sorted(set(on_time) | set(late), key=lambda s: -(on_time[s] + late[s]))
	if not staff:
		return None
	return {
		"data": {
			"labels": staff,
			"datasets": [
				{"name": CALLED, "values": [on_time[s] for s in staff]},
				{"name": CALLED_LATE, "values": [late[s] for s in staff]},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
		"colors": ["#28a745", "#fd7e14"],
	}
