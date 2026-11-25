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
from frappe.utils import add_months, cint, getdate, today

from bb_tution_management.bb_academy.pending_calls import (
	ATTENDED,
	CLOSED,
	DOCTYPE,
	NOT_ATTENDED,
	PRIORITIES,
	_guard,
	_phones,
	_resolve_month,
	missed_calls,
	new_call_log,
	not_attended_counts,
	priority_level,
)
from bb_tution_management.bb_academy.pending_calls import priority_label as _priority_label
from bb_tution_management.bb_academy.syllabus import (
	lesson_titles,
	syllabus_lessons,
	syllabus_of,
	syllabus_text,
)

ATTENDANCE_DOCTYPE = "Student Attendance"
CATEGORY = "Attendance"
STATUSES = ["Absent", "Late"]

# Absent + Late days in a month at which the parents must also come in and meet
# the staff -- the same 5 as Student Mistakes. Until that meeting is on file
# (informed, met, staff named, photo uploaded) the card stays on the list and
# cannot be closed.
MEETING_THRESHOLD = 5
MEETING_DOCTYPE = "Attendance Parent Meeting"
MEETING_FIELDS = [
	"name",
	"student",
	"parents_informed",
	"parents_informed_on",
	"meeting_done",
	"met_staff",
	"meeting_on",
	"meeting_photo",
	"meeting_notes",
]


def meeting_name(student, month_start):
	from bb_tution_management.bb_academy.performance_config import slug

	return f"APM-{getdate(month_start).strftime('%Y-%m')}-{slug(student)}"


def meeting_complete(meeting):
	return bool(
		meeting
		and cint(meeting.get("parents_informed"))
		and cint(meeting.get("meeting_done"))
		and meeting.get("met_staff")
		and meeting.get("meeting_photo")
	)


def _meetings(first_day, students=None):
	filters = {"month_start": first_day}
	if students is not None:
		filters["student"] = ["in", list(students) or [""]]
	return {
		m.student: m
		for m in frappe.get_all(MEETING_DOCTYPE, filters=filters, fields=MEETING_FIELDS)
	}


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
			a.status, a.remarks, a.standard, a.batch,
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

	from bb_tution_management.bb_academy.complaints import open_complaints

	meetings = _meetings(first_day)
	complaints = open_complaints(complaint_for="Attendance")

	# Listed while a call is owed, while a parent meeting the count demands is
	# not yet on file, or while a parent's complaint is unsolved.
	pending = {}
	for student, rows in by_student.items():
		level = priority_level(len(rows))
		called_level = priority_level(sum(1 for r in rows if r.called))
		meeting_due = len(rows) >= MEETING_THRESHOLD and not meeting_complete(meetings.get(student))
		if level > called_level or meeting_due or complaints.get(student):
			pending[student] = (rows, level, called_level)

	# A complaint keeps the student listed even with no Absent day this month.
	extra = [s for s in complaints if s not in pending]
	if extra:
		student_filters = {"name": ["in", extra], "status": "Active"}
		for field, column, value in (
			("standard", "standard", standard),
			("batch", "current_batch", batch),
			("gender", "gender", gender),
		):
			if value:
				student_filters[column] = value
		for s in frappe.get_all("Student", filters=student_filters, pluck="name"):
			pending[s] = (by_student.get(s, []), 0, 0)

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
		SELECT c.student, c.called_on, c.called_by, c.spoken_to,
			IFNULL(c.call_status, 'Attended') AS call_status
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

	not_attended = not_attended_counts(list(pending), "Attendance", first_day)

	records = []
	for student_id, (rows, level, called_level) in pending.items():
		student = students.get(student_id)
		if not student:
			continue

		# The day the count entered its current priority.
		if level:
			due_since = getdate(rows[PRIORITIES[level - 1][0] - 1].date)
		elif rows:
			due_since = getdate(rows[-1].date)
		else:
			due_since = getdate(today())
		meeting = meetings.get(student_id)
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
				"not_attended": not_attended.get(student_id, 0),
				# Uncovered days a call or Close can still pin.
				"call_due": level > called_level,
				"meeting_required": len(rows) >= MEETING_THRESHOLD,
				"meeting": meeting,
				"meeting_complete": meeting_complete(meeting),
				"open_complaints": complaints.get(student_id, 0),
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
	_attach_missed_sessions(rows)
	return {"days": rows}


# What a batch's day is made of, in the order the screen lists it. Behaviour is
# left out: it grades the students in the room, it is not something taught.
SESSION_CATEGORIES = ["Class", "Study", "Test", "H.W"]


def _batch_on(student):
	"""A function giving the batch the student sat in on a given date.

	Attendance rows do not store a batch, and batch names ("I", "II") repeat
	across standards, so the batch is rebuilt from the student's current batch
	and their transitions: before a move they were in its previous batch.
	"""
	current = frappe.db.get_value("Student", student, "current_batch")
	moves = frappe.db.sql(
		"""
		SELECT effective_date, previous_batch
		FROM `tabStudent Batch Transition`
		WHERE student = %(student)s AND docstatus < 2 AND effective_date IS NOT NULL
		ORDER BY effective_date ASC, creation ASC
		""",
		{"student": student},
		as_dict=True,
	)

	def batch_on(date):
		date = getdate(date)
		for move in moves:
			if getdate(move.effective_date) > date and move.previous_batch:
				return move.previous_batch
		return current

	return batch_on


def _attach_missed_sessions(rows):
	"""Give every day the Class / Study / Test / H.W its batch had that day --
	what the student missed by being absent, or walked in late on."""
	for row in rows:
		row["missed"] = []
	if not rows:
		return

	batch_on = _batch_on(rows[0].student)
	for row in rows:
		row["batch"] = row.batch or batch_on(row.date)

	dates = {getdate(r.date) for r in rows}
	batches = {r.batch for r in rows if r.batch}
	if not batches:
		return

	sessions = frappe.db.sql(
		"""
		SELECT name, date, standard, batch, category, subject, total_marks, pass_marks,
			no_session, no_session_reason
		FROM `tabStudent Performance Session`
		WHERE date IN %(dates)s AND batch IN %(batches)s AND category IN %(categories)s
		ORDER BY creation ASC
		""",
		{
			"dates": tuple(dates),
			"batches": tuple(batches),
			"categories": tuple(SESSION_CATEGORIES),
		},
		as_dict=True,
	)
	if not sessions:
		return

	syllabus = syllabus_of("Student Performance Session", [s.name for s in sessions])
	titles = lesson_titles(
		[lesson for blocks in syllabus.values() for lesson in syllabus_lessons(blocks)]
	)

	by_day = {}
	for s in sessions:
		by_day.setdefault((getdate(s.date), s.standard, s.batch), []).append(
			{
				"name": s.name,
				"category": s.category,
				"topic": syllabus_text(syllabus.get(s.name, []), titles) or s.subject or "",
				# Subject / Lesson / Portion kept apart so the screen can label each.
				"blocks": [
					{
						"subject": block["subject"],
						"lessons": [titles.get(n, n) for n in block["lessons"]],
						"portions": block["portions"],
					}
					for block in syllabus.get(s.name, [])
				]
				or ([{"subject": s.subject, "lessons": [], "portions": []}] if s.subject else []),
				"total_marks": s.total_marks,
				"pass_marks": s.pass_marks,
				"no_session": cint(s.no_session),
				"no_session_reason": s.no_session_reason,
			}
		)

	order = {c: i for i, c in enumerate(SESSION_CATEGORIES)}
	for row in rows:
		found = by_day.get((getdate(row.date), row.standard, row.batch), [])
		row["missed"] = sorted(found, key=lambda item: order.get(item["category"], 99))


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

	doc = new_call_log(
		student,
		ATTENDED,
		"Attendance",
		_items(rows),
		spoken_to=spoken_to,
		spoken_to_name=spoken_to_name,
		called_on=called_on,
		called_by=called_by,
		call_notes=call_notes,
	)
	return {"name": doc.name, "days": len(rows)}


def _items(rows):
	return [
		{
			"category": CATEGORY,
			"mistake_date": row.date,
			"result": row.status,
			"details": (row.remarks or "")[:140],
			"reference_doctype": ATTENDANCE_DOCTYPE,
			"reference_name": row.reference_name,
		}
		for row in rows
	]


@frappe.whitelist()
def close_student(student, call_notes=None):
	"""Take the student off the list without a call. The month's uncovered
	days are pinned to a Closed log, so -- like a call -- the student returns
	only on reaching the next priority."""
	_guard("create")
	_guard_close(student)

	rows = [r for r in _month_rows(_this_month(), student=student) if not r.called]
	if not rows:
		frappe.throw(frappe._("There are no Absent or Late days this month left to close."))

	doc = new_call_log(student, CLOSED, "Attendance", _items(rows), call_notes=call_notes)
	return {"name": doc.name, "days": len(rows)}


def _guard_close(student):
	"""Close is refused while the parents still have something owed to them."""
	from bb_tution_management.bb_academy.complaints import has_open_complaint

	missing = []
	if has_open_complaint(student, "Attendance"):
		missing.append(
			"the parents' complaint is still open — call them back and solve it on Complaint Calls"
		)
	first_day = _this_month()
	if len(_month_rows(first_day, student=student)) >= MEETING_THRESHOLD and not meeting_complete(
		_meetings(first_day, [student]).get(student)
	):
		missing.append(
			"the parent meeting is not complete (informed, met, staff and photo are all needed)"
		)
	if missing:
		frappe.throw(
			frappe._("This student cannot be closed yet — {0}.").format("; ".join(missing)),
			title=frappe._("Follow-up Incomplete"),
		)


def _meeting_doc(student):
	first_day = _this_month()
	name = meeting_name(student, first_day)
	if frappe.db.exists(MEETING_DOCTYPE, name):
		return frappe.get_doc(MEETING_DOCTYPE, name)
	doc = frappe.new_doc(MEETING_DOCTYPE)
	doc.student = student
	doc.month_start = first_day
	return doc


@frappe.whitelist()
def record_meeting(
	student,
	parents_informed=None,
	meeting_done=None,
	met_staff=None,
	meeting_on=None,
	meeting_notes=None,
):
	"""This month's parent meeting for one student: informed, met, notes."""
	_guard("create")
	doc = _meeting_doc(student)
	doc.absent_late_count = len(_month_rows(_this_month(), student=student))
	doc.parents_informed = cint(parents_informed)
	doc.meeting_done = cint(meeting_done)
	doc.met_staff = met_staff or None
	if meeting_on:
		doc.meeting_on = meeting_on
	doc.meeting_notes = meeting_notes
	doc.save(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def attach_meeting_photo(name, file_url):
	"""Point the meeting at a photo already uploaded through upload_file."""
	_guard("create")
	doc = frappe.get_doc(MEETING_DOCTYPE, name)

	owner_doctype, owner_name = frappe.db.get_value(
		"File", {"file_url": file_url}, ["attached_to_doctype", "attached_to_name"]
	) or (None, None)
	if not frappe.db.exists("File", {"file_url": file_url}):
		frappe.throw(frappe._("Upload the photo first."))
	if owner_doctype and (owner_doctype != MEETING_DOCTYPE or owner_name != doc.name):
		frappe.throw(frappe._("That file belongs to another document."))

	doc.meeting_photo = file_url
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "meeting_photo": doc.meeting_photo}


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
		"not_attended": NOT_ATTENDED,
	}
	conditions = [
		"c.called_on >= %(first_day)s",
		"c.called_on < %(next_month)s",
		"(i.name IS NOT NULL OR (c.call_for = 'Attendance' AND c.call_status = %(not_attended)s))",
	]
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
			IFNULL(c.call_status, 'Attended') AS call_status, c.owner,
			SUM(i.result = 'Absent') AS absent,
			SUM(i.result = 'Late') AS late,
			MIN(i.mistake_date) AS first_day
		FROM `tabParent Call Log` c
		LEFT JOIN `tabParent Call Log Item` i
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
		call["closed_by"] = frappe.utils.get_fullname(call.owner)
		if call.call_status == NOT_ATTENDED:
			# Covered nothing: no count or priority of its own.
			call["count"] = None
			call["priority"] = None
			continue
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
