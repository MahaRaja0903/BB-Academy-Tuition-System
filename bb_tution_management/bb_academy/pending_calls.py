"""Pending Call Works: the students whose parents are owed a phone call.

A student lands on the list once they have THRESHOLD mistakes in any one
category -- H.W, Attendance, Test, Study, Class or Behaviour -- and leaves it the
moment staff log the call. Each category keeps its own count.

What restarts the count is the call itself: a Parent Call Log records the exact
mistakes it told the parents about, and only mistakes no call has covered are
counted. So a student who misses home work twice after the call is on 2, not
on 2 plus everything before it. Nothing is stored about the count -- it is
derived live every time, so re-grading a row corrects the list with it.

A mistake is:

    H.W / Test / Study / Class / Behaviour   a tracker row graded with one of
                                             LOW_RESULTS (Skipped never counts)
    Attendance                               a Student Attendance row marked
                                             Absent
"""

import json

import frappe
from frappe.utils import add_months, cint, flt, get_datetime, get_first_day, getdate, now_datetime, today

from bb_tution_management.bb_academy.performance_config import LOW_RESULTS

DOCTYPE = "Parent Call Log"
TRACKER = "Student Performance Tracker"
ATTENDANCE_DOCTYPE = "Student Attendance"

ATTENDANCE = "Attendance"
# The order the screen shows them in.
CATEGORIES = ["H.W", ATTENDANCE, "Test", "Study", "Class", "Behaviour"]
TRACKER_CATEGORIES = [c for c in CATEGORIES if c != ATTENDANCE]

ABSENT_STATUSES = ["Absent"]

DEFAULT_THRESHOLD = 3


def _setting(fieldname):
	"""The raw stored value, or None. get_single_value casts an unset Date to
	0001-01-01, which would read as "count from the beginning of time"."""
	row = frappe.db.sql(
		"SELECT value FROM `tabSingles` WHERE doctype = 'BB Academy Settings' AND field = %s",
		fieldname,
	)
	return row[0][0] if row and row[0][0] else None


def threshold():
	value = cint(_setting("pending_call_threshold"))
	return value if value > 0 else DEFAULT_THRESHOLD


def count_from():
	"""Mistakes before this date are history the screen never reaches back to.

	Without a floor, the first day the screen is opened every student with three
	missed home works in the last two years would be "owed" a call.
	"""
	value = _setting("pending_calls_from")
	return getdate(value) if value else get_first_day(getdate(today()))


def _guard(ptype="read"):
	if not frappe.has_permission(DOCTYPE, ptype):
		frappe.throw(
			frappe._("Not permitted to {0} Parent Call Logs").format(ptype),
			frappe.PermissionError,
		)


def _uncovered_mistakes(student=None, standard=None, batch=None, gender=None, categories=None):
	"""Every mistake since `count_from()` that no call has told the parents about.

	Only Active students: a discontinued student's parents are not called about
	home work.
	"""
	categories = [c for c in (categories or CATEGORIES) if c in CATEGORIES]
	if not categories:
		return []

	values = {"from_date": count_from()}
	student_conditions = ["s.status = 'Active'"]
	for field, column, value in (
		("student", "s.name", student),
		("standard", "s.standard", standard),
		("batch", "s.current_batch", batch),
		("gender", "s.gender", gender),
	):
		if value:
			student_conditions.append(f"{column} = %({field})s")
			values[field] = value
	student_where = " AND ".join(student_conditions)

	rows = []

	tracker_categories = [c for c in categories if c in TRACKER_CATEGORIES]
	if tracker_categories:
		values["tracker_categories"] = tuple(tracker_categories)
		values["low_results"] = tuple(LOW_RESULTS)
		rows += frappe.db.sql(
			f"""
			SELECT %(tracker)s AS reference_doctype, t.name AS reference_name,
				t.student, t.category, t.date, t.result, t.subject, t.remarks,
				t.marks_obtained, t.total_marks
			FROM `tabStudent Performance Tracker` t
			INNER JOIN `tabStudent` s ON s.name = t.student
			WHERE {student_where}
				AND t.date >= %(from_date)s
				AND t.category IN %(tracker_categories)s
				AND t.result IN %(low_results)s
				AND NOT EXISTS (
					SELECT 1 FROM `tabParent Call Log Item` i
					WHERE i.reference_name = t.name AND i.reference_doctype = %(tracker)s
				)
			""",
			{**values, "tracker": TRACKER},
			as_dict=True,
		)

	if ATTENDANCE in categories:
		values["absent"] = tuple(ABSENT_STATUSES)
		rows += frappe.db.sql(
			f"""
			SELECT %(attendance)s AS reference_doctype, a.name AS reference_name,
				a.student, 'Attendance' AS category, a.attendance_date AS date,
				a.status AS result, NULL AS subject, a.remarks,
				NULL AS marks_obtained, NULL AS total_marks
			FROM `tabStudent Attendance` a
			INNER JOIN `tabStudent` s ON s.name = a.student
			WHERE {student_where}
				AND a.docstatus < 2
				AND a.attendance_date >= %(from_date)s
				AND a.status IN %(absent)s
				AND NOT EXISTS (
					SELECT 1 FROM `tabParent Call Log Item` i
					WHERE i.reference_name = a.name AND i.reference_doctype = %(attendance)s
				)
			""",
			{**values, "attendance": ATTENDANCE_DOCTYPE},
			as_dict=True,
		)

	rows.sort(key=lambda r: (getdate(r.date), r.reference_name))
	return rows


def _details(row):
	"""One short line saying what the mistake was."""
	if row.get("total_marks"):
		text = f"{flt(row.marks_obtained):g} / {flt(row.total_marks):g}"
		return f"{row.subject} · {text}" if row.get("subject") else text
	return row.get("subject") or ""


def _phones(student):
	"""Numbers to ring, the family's preferred one first."""
	numbers = [
		("Father", student.father_mobile_number),
		("Mother", student.mother_mobile_number),
		("Guardian", student.guardian_mobile_number),
	]
	numbers = [{"label": label, "number": number} for label, number in numbers if number]
	preferred = student.preferred_mobile_number
	numbers.sort(key=lambda p: 0 if p["label"] == preferred else 1)
	return numbers


@frappe.whitelist()
def get_pending_calls(standard=None, batch=None, gender=None):
	"""Students with at least one category at or over the threshold."""
	_guard("read")

	limit = threshold()
	by_student = {}
	for row in _uncovered_mistakes(standard=standard, batch=batch, gender=gender):
		by_student.setdefault(row.student, {}).setdefault(row.category, []).append(row)

	pending = {}
	for student, by_category in by_student.items():
		due = {c: rows for c, rows in by_category.items() if len(rows) >= limit}
		if due:
			pending[student] = by_category

	if not pending:
		return {"records": [], "threshold": limit, "count_from": count_from()}

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
		SELECT student, called_on, called_by, spoken_to, categories
		FROM `tabParent Call Log`
		WHERE student IN %(students)s
		ORDER BY called_on DESC
		""",
		{"students": tuple(pending)},
		as_dict=True,
	):
		last_calls.setdefault(call.student, call)

	records = []
	for student_id, by_category in pending.items():
		student = students.get(student_id)
		if not student:
			continue

		categories = []
		for category in CATEGORIES:
			rows = by_category.get(category, [])
			if not rows:
				continue
			categories.append(
				{
					"category": category,
					"count": len(rows),
					"due": len(rows) >= limit,
					# The day the count reached the threshold: how long the
					# family has been waiting for the call.
					"due_since": getdate(rows[limit - 1].date) if len(rows) >= limit else None,
					"last_mistake_on": getdate(rows[-1].date),
				}
			)

		due_since = min(c["due_since"] for c in categories if c["due"])
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
				"categories": categories,
				"due_categories": [c["category"] for c in categories if c["due"]],
				"total_mistakes": sum(c["count"] for c in categories),
				"due_since": due_since,
				"days_pending": (getdate(today()) - due_since).days,
				"last_call": last_calls.get(student_id),
			}
		)

	# Longest-waiting family first.
	records.sort(key=lambda r: (r["due_since"], -r["total_mistakes"], r["student_name"] or ""))
	return {"records": records, "threshold": limit, "count_from": count_from()}


@frappe.whitelist()
def get_student_mistakes(student):
	"""The uncovered mistakes behind one student's counts, newest first."""
	_guard("read")

	rows = _uncovered_mistakes(student=student)
	for row in rows:
		row["details"] = _details(row)
	rows.reverse()
	return {"mistakes": rows}


@frappe.whitelist()
def log_call(
	student,
	categories,
	spoken_to=None,
	spoken_to_name=None,
	called_on=None,
	called_by=None,
	call_notes=None,
):
	"""Record the call home. Every mistake not yet covered in the chosen
	categories is pinned to it, so each of their counts starts again at zero.

	The mistakes are read here, not sent by the browser: the call covers what
	was on file when it was logged, including a grade entered while the dialog
	was open.
	"""
	_guard("create")

	if isinstance(categories, str):
		categories = json.loads(categories)
	categories = [c for c in (categories or []) if c in CATEGORIES]
	if not categories:
		frappe.throw(frappe._("Pick at least one category the parents were told about."))
	if not spoken_to:
		frappe.throw(frappe._("Say whom you spoke to."))
	if not called_by:
		frappe.throw(frappe._("Say who made the call."))
	if not (call_notes or "").strip():
		frappe.throw(frappe._("Write down what was spoken."))

	rows = _uncovered_mistakes(student=student, categories=categories)
	if not rows:
		frappe.throw(frappe._("There are no pending mistakes in those categories to inform."))

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
				"category": row.category,
				"mistake_date": row.date,
				"result": row.result,
				"details": _details(row)[:140],
				"reference_doctype": row.reference_doctype,
				"reference_name": row.reference_name,
			},
		)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "mistakes": len(rows)}


def _resolve_month(month):
	if not month:
		return get_first_day(getdate(today()))
	if isinstance(month, str) and len(month) == 7:
		return get_first_day(getdate(f"{month}-01"))
	return get_first_day(getdate(month))


@frappe.whitelist()
def get_call_history(month=None, standard=None, batch=None, gender=None):
	"""Calls made in one month, newest first."""
	_guard("read")

	first_day = _resolve_month(month)
	values = {"first_day": first_day, "next_month": add_months(first_day, 1)}
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
			c.categories, c.mistake_count
		FROM `tabParent Call Log` c
		LEFT JOIN `tabStudent` s ON s.name = c.student
		WHERE {" AND ".join(conditions)}
		ORDER BY c.called_on DESC
		""",
		values,
		as_dict=True,
	)

	if calls:
		counts = frappe.db.sql(
			"""
			SELECT parent, category, COUNT(name) AS mistakes
			FROM `tabParent Call Log Item`
			WHERE parenttype = %(doctype)s AND parent IN %(parents)s
			GROUP BY parent, category
			""",
			{"doctype": DOCTYPE, "parents": tuple(c.name for c in calls)},
			as_dict=True,
		)
		by_parent = {}
		for row in counts:
			by_parent.setdefault(row.parent, {})[row.category] = row.mistakes
		for call in calls:
			found = by_parent.get(call.name, {})
			call["breakdown"] = [
				{"category": c, "count": found[c]} for c in CATEGORIES if c in found
			]

	return {"calls": calls}
