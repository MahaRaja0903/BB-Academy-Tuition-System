"""Student Mistake Records: the monthly follow-up a student's mistakes trigger.

A "mistake" is one Student Performance Tracker row graded with a LOW_RESULT --
Incomplete, Fail, Bad or Worst. Skipped is not a mistake: the teacher excused
the student. The count is always derived from the tracker, never typed in, so
correcting a wrongly graded test corrects the follow-up with it.

Three thresholds, cumulative -- a student on 6 still owes the call that fell due
at 3:

      3-4   call home, recording whom was spoken to, what, when and by whom
      5-9   parents informed, parents meet the staff, photo taken and uploaded
      10+   Test / Study / Behaviour each reviewed separately for the month

The record stays on the staff's list until it is closed, and closing is refused
while any action its level demands is still missing. A mistake made after
closure pushes the count past `closed_at_count` and reopens it.
"""

import json

import frappe
from frappe.utils import cint, get_first_day, get_last_day, getdate, now_datetime, today

from bb_tution_management.bb_academy.performance_config import LOW_RESULTS, slug

THRESHOLD_CALL = 3
THRESHOLD_MEETING = 5
THRESHOLD_CATEGORY = 10

LEVEL_CALL = "Call"
LEVEL_MEETING = "Parent Meeting"
LEVEL_CATEGORY = "Category Review"

# The three buckets the monthly review is kept in.
REVIEW_CATEGORIES = ["Test", "Study", "Behaviour"]

_CATEGORY_BUCKET = {
	"Study": "Study",
	"Test": "Test",
	"Behaviour": "Behaviour",
}

DOCTYPE = "Student Mistake Record"


def bucket_for_category(category):
	"""Which of Test / Study / Behaviour a tracker category counts towards."""
	return _CATEGORY_BUCKET.get(category)


def record_name(student, month_start):
	"""Deterministic name, so the same student-month can only ever hold one
	record however many writers race for it."""
	return f"MIS-{getdate(month_start).strftime('%Y-%m')}-{slug(student)}"


def month_bounds(date=None):
	date_obj = getdate(date or today())
	return get_first_day(date_obj), get_last_day(date_obj)


def month_label(month_start):
	return getdate(month_start).strftime("%B %Y")


def last_batch_change(student, first_day, last_day):
	"""The date this student moved batch within the given month, if they did.

	A batch move is the end of a follow-up, not a footnote to it: the teacher
	speaks to the parents and moves the student precisely so they can start
	again. Counting the old batch's mistakes against them in the new one would
	make that fresh start impossible -- the record would reopen on history.

	Cancelled transitions are ignored; drafts are not, because the Student form
	records a batch change as a draft transition *after* already moving the
	student, so waiting for a submit would miss the commonest case.
	"""
	row = frappe.db.sql(
		"""
		SELECT effective_date, previous_batch, new_batch
		FROM `tabStudent Batch Transition`
		WHERE student = %(student)s
			AND docstatus < 2
			AND effective_date BETWEEN %(first_day)s AND %(last_day)s
			AND IFNULL(new_batch, '') != ''
		ORDER BY effective_date DESC, modified DESC
		LIMIT 1
		""",
		{"student": student, "first_day": first_day, "last_day": last_day},
		as_dict=True,
	)
	return row[0] if row else None


def count_mistakes(student, date=None):
	"""This month's mistakes for one student, split by review bucket.

	The window is the calendar month, unless the student changed batch inside
	it -- then it starts on the day of the move, so the new batch begins at
	zero.
	"""
	first_day, last_day = month_bounds(date)

	move = last_batch_change(student, first_day, last_day)
	count_from = getdate(move.effective_date) if move else first_day

	rows = frappe.db.sql(
		"""
		SELECT category, COUNT(name) AS entries, MAX(date) AS last_date
		FROM `tabStudent Performance Tracker`
		WHERE student = %(student)s
			AND date BETWEEN %(count_from)s AND %(last_day)s
			AND result IN %(low_results)s
		GROUP BY category
		""",
		{
			"student": student,
			"count_from": count_from,
			"last_day": last_day,
			"low_results": tuple(LOW_RESULTS),
		},
		as_dict=True,
	)

	counts = {bucket: 0 for bucket in REVIEW_CATEGORIES}
	last_mistake_on = None

	for row in rows:
		bucket = bucket_for_category(row.category)
		if not bucket:
			# A category retired from performance_config still has history in
			# the tracker; it is counted in the total but has no review bucket.
			continue
		counts[bucket] += cint(row.entries)
		if row.last_date and (not last_mistake_on or getdate(row.last_date) > last_mistake_on):
			last_mistake_on = getdate(row.last_date)

	return {
		"counts": counts,
		"total": sum(counts.values()),
		"last_mistake_on": last_mistake_on,
		"month_start": first_day,
		"count_from": count_from,
		"batch_changed_on": getdate(move.effective_date) if move else None,
		"moved_from_batch": move.previous_batch if move else None,
		"moved_to_batch": move.new_batch if move else None,
	}


def _student_snapshot(student):
	return (
		frappe.db.get_value(
			"Student",
			student,
			["student_name", "standard", "current_batch", "gender"],
			as_dict=True,
		)
		or frappe._dict()
	)


def _is_untouched(doc):
	"""Nothing a human entered would be lost by deleting this record."""
	if doc.call_done or doc.parents_informed or doc.meeting_done or doc.meeting_photo:
		return False
	if (doc.call_notes or doc.meeting_notes or doc.closure_notes or "").strip():
		return False
	for row in doc.category_breakdown or []:
		if row.reviewed or (row.what_happened or "").strip() or (row.action_taken or "").strip():
			return False
	return True


def _sync_category_rows(doc, counts):
	"""Keep one review row per category, preserving whatever staff wrote in it."""
	if not doc.category_review_required:
		return

	existing = {row.category: row for row in (doc.category_breakdown or [])}
	rows = []
	for category in REVIEW_CATEGORIES:
		row = existing.get(category)
		rows.append(
			{
				"category": category,
				"mistake_count": counts.get(category, 0),
				"reviewed": cint(row.reviewed) if row else 0,
				"what_happened": (row.what_happened if row else None),
				"action_taken": (row.action_taken if row else None),
			}
		)

	doc.set("category_breakdown", [])
	for row in rows:
		doc.append("category_breakdown", row)


def sync_student_month(student, date=None):
	"""Bring one student's record for `date`'s month in line with the tracker.

	Returns the record name, or None when the student is below the first
	threshold and has no record worth keeping.
	"""
	if not student:
		return None

	tally = count_mistakes(student, date)
	total = tally["total"]
	month_start = tally["month_start"]
	name = record_name(student, month_start)
	exists = frappe.db.exists(DOCTYPE, name)

	if total < THRESHOLD_CALL:
		# Dropped back under the first threshold -- a mis-grade that was
		# corrected, or a batch move that restarted the count. Drop the record
		# only if no one has acted on it yet.
		if exists:
			doc = frappe.get_doc(DOCTYPE, name)
			if _is_untouched(doc):
				doc.delete(ignore_permissions=True)
				return None
			doc.mistake_count = total
			_write_tally(doc, tally)
			# The move *is* the outcome of the follow-up that prompted it, so
			# the record has nothing left to chase. Left open it would sit on
			# the staff's list for the rest of the month reading "0 mistakes".
			# The call and meeting already recorded stay on it as the history.
			if doc.status == "Open" and tally["batch_changed_on"]:
				doc.status = "Closed"
				doc.closure_notes = _batch_move_note(tally, doc.closure_notes)
				doc.flags.ignore_closure_guard = True
			doc.save(ignore_permissions=True)
			return doc.name
		return None

	student_row = _student_snapshot(student)

	if exists:
		doc = frappe.get_doc(DOCTYPE, name)
	else:
		doc = frappe.new_doc(DOCTYPE)
		doc.student = student
		doc.month_start = month_start
		doc.status = "Open"

	# A mistake made after the record was closed reopens it: the follow-up the
	# staff signed off on no longer covers everything the student has done.
	if doc.status == "Closed" and total > cint(doc.closed_at_count):
		doc.status = "Open"

	doc.student_name = student_row.get("student_name")
	doc.standard = student_row.get("standard")
	doc.batch = student_row.get("current_batch")
	doc.gender = student_row.get("gender")
	doc.month_label = month_label(month_start)
	doc.mistake_count = total
	_write_tally(doc, tally)

	# set_action_level() runs in validate(), but the category rows are built
	# from the flag, so it has to be settled before they are laid out.
	doc.category_review_required = 1 if total >= THRESHOLD_CATEGORY else 0
	_sync_category_rows(doc, tally["counts"])

	if exists:
		doc.save(ignore_permissions=True)
	else:
		doc.insert(ignore_permissions=True)

	return doc.name


def _batch_move_note(tally, existing=None):
	"""Why a record with a completed follow-up is being closed at zero."""
	moved = " to Batch {0}".format(tally["moved_to_batch"]) if tally["moved_to_batch"] else ""
	note = frappe._(
		"Closed automatically: the student moved{0} on {1}, so the mistake count "
		"restarts from that date. The follow-up recorded above stands as the history."
	).format(moved, frappe.format_value(tally["batch_changed_on"], {"fieldtype": "Date"}))

	existing = (existing or "").strip()
	return f"{existing}\n\n{note}" if existing else note


def _write_tally(doc, tally):
	counts = tally["counts"]
	doc.test_count = counts.get("Test", 0)
	doc.study_count = counts.get("Study", 0)
	doc.behaviour_count = counts.get("Behaviour", 0)
	doc.last_mistake_on = tally["last_mistake_on"]
	# What window the count covers. Stored rather than re-derived so the screen
	# can say why a student who clearly had a bad month reads as 1 mistake.
	doc.count_from = tally["count_from"]
	doc.batch_changed_on = tally["batch_changed_on"]


def sync_from_tracker(doc, method=None):
	"""doc_event on Student Performance Tracker.

	A grade that moved student or month has to settle both sides, or the row it
	left behind keeps counting against the old record.
	"""
	pairs = {(doc.student, getdate(doc.date))}

	before = doc.get_doc_before_save() if method != "after_delete" else None
	if before and before.student and before.date:
		pairs.add((before.student, getdate(before.date)))

	for student, date in pairs:
		if student and date:
			sync_student_month(student, date)


def sync_month(date=None, standard=None):
	"""Rebuild every record for one month. Used by the nightly job and by the
	Rebuild action, so a record is never left stale by an import or a patch."""
	first_day, last_day = month_bounds(date)

	filters = {
		"first_day": first_day,
		"last_day": last_day,
		"low_results": tuple(LOW_RESULTS),
	}
	standard_filter = ""
	if standard:
		standard_filter = "AND t.standard = %(standard)s"
		filters["standard"] = standard

	students = frappe.db.sql_list(
		f"""
		SELECT DISTINCT t.student
		FROM `tabStudent Performance Tracker` t
		WHERE t.date BETWEEN %(first_day)s AND %(last_day)s
			AND t.result IN %(low_results)s
			{standard_filter}
		""",
		filters,
	)

	# Records already open this month whose last mistake was undone still need a
	# pass, or they would sit on the list for ever.
	students += frappe.db.sql_list(
		"""
		SELECT student FROM `tabStudent Mistake Record` WHERE month_start = %(first_day)s
		""",
		{"first_day": first_day},
	)

	synced = 0
	for student in set(students):
		sync_student_month(student, first_day)
		synced += 1

	return {"month": month_label(first_day), "students": synced}


def sync_current_month():
	"""Nightly self-heal for the running month."""
	return sync_month(today())


# ---------------------------------------------------------------------------
# API for the Student Mistakes screen
# ---------------------------------------------------------------------------


def _guard(ptype="read"):
	if not frappe.has_permission(DOCTYPE, ptype):
		frappe.throw(
			frappe._("Not permitted to {0} Student Mistake Records").format(ptype),
			frappe.PermissionError,
		)


def _resolve_month(month):
	"""Accepts "YYYY-MM", any date in the month, or nothing for this month."""
	if not month:
		return get_first_day(getdate(today()))
	if isinstance(month, str) and len(month) == 7:
		return get_first_day(getdate(f"{month}-01"))
	return get_first_day(getdate(month))


@frappe.whitelist()
def get_mistake_students(
	standard=None, batch=None, gender=None, month=None, status="Open", search=None
):
	"""The follow-up list. Closed records drop out unless asked for by name."""
	_guard("read")

	conditions = []
	values = {}

	if month != "all":
		values["month_start"] = _resolve_month(month)
		conditions.append("r.month_start = %(month_start)s")

	if status and status != "all":
		conditions.append("r.status = %(status)s")
		values["status"] = status

	for field, value in (("standard", standard), ("batch", batch), ("gender", gender)):
		if value:
			conditions.append(f"r.{field} = %({field})s")
			values[field] = value

	if search:
		conditions.append("(r.student_name LIKE %(search)s OR r.student LIKE %(search)s)")
		values["search"] = f"%{search}%"

	where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

	records = frappe.db.sql(
		f"""
		SELECT r.name, r.student, r.student_name, r.standard, r.batch, r.gender,
			r.month_start, r.month_label, r.mistake_count, r.action_level, r.status,
			r.test_count, r.study_count, r.behaviour_count, r.last_mistake_on,
			r.count_from, r.batch_changed_on,
			r.call_required, r.call_done, r.spoken_to, r.spoken_to_name,
			r.called_on, r.called_by, r.call_notes,
			r.meeting_required, r.parents_informed, r.parents_informed_on,
			r.meeting_done, r.met_staff, r.meeting_on, r.meeting_photo, r.meeting_notes,
			r.category_review_required, r.closure_notes, r.closed_on, r.closed_by,
			r.reopened_on,
			s.image
		FROM `tabStudent Mistake Record` r
		LEFT JOIN `tabStudent` s ON s.name = r.student
		{where}
		ORDER BY r.mistake_count DESC, r.student_name ASC
		""",
		values,
		as_dict=True,
	)

	if records:
		breakdowns = frappe.db.sql(
			"""
			SELECT parent, category, mistake_count, reviewed, what_happened, action_taken
			FROM `tabStudent Mistake Category Item`
			WHERE parent IN %(parents)s
			ORDER BY idx ASC
			""",
			{"parents": tuple(r.name for r in records)},
			as_dict=True,
		)
		by_parent = {}
		for row in breakdowns:
			by_parent.setdefault(row.parent, []).append(row)
		for record in records:
			record["category_breakdown"] = by_parent.get(record.name, [])
			record["pending"] = _pending_actions(record)

	return {"records": records}


def _pending_actions(record):
	"""What still stands between this record and being closable."""
	pending = []

	if cint(record.get("call_required")) and not cint(record.get("call_done")):
		pending.append("Call home")
	if cint(record.get("meeting_required")):
		if not cint(record.get("parents_informed")):
			pending.append("Inform parents")
		if not cint(record.get("meeting_done")):
			pending.append("Parent meeting")
		elif not record.get("meeting_photo"):
			pending.append("Meeting photo")
	if cint(record.get("category_review_required")):
		rows = record.get("category_breakdown") or []
		unreviewed = [row.get("category") for row in rows if not cint(row.get("reviewed"))]
		if not rows:
			pending.append("Category review")
		elif unreviewed:
			pending.append("Review " + ", ".join(unreviewed))

	return pending


@frappe.whitelist()
def get_mistake_detail(record):
	"""The tracker rows the count is made of, newest first.

	Read live rather than copied onto the record, so a re-grade shows through
	immediately instead of leaving the follow-up quoting a stale mistake.
	"""
	_guard("read")

	doc = frappe.get_doc(DOCTYPE, record)
	first_day, last_day = month_bounds(doc.month_start)

	rows = frappe.db.sql(
		"""
		SELECT name, date, category, result, remarks, subject, lesson, marks_obtained, total_marks
		FROM `tabStudent Performance Tracker`
		WHERE student = %(student)s
			AND date BETWEEN %(first_day)s AND %(last_day)s
			AND result IN %(low_results)s
		ORDER BY date DESC, category ASC
		""",
		{
			"student": doc.student,
			"first_day": first_day,
			"last_day": last_day,
			"low_results": tuple(LOW_RESULTS),
		},
		as_dict=True,
	)

	if rows:
		reasons = frappe.db.sql(
			"""
			SELECT parent, behaviour_reason
			FROM `tabStudent Behaviour Reason Item`
			WHERE parenttype = 'Student Performance Tracker' AND parent IN %(parents)s
			""",
			{"parents": tuple(r.name for r in rows)},
			as_dict=True,
		)
		by_parent = {}
		for row in reasons:
			by_parent.setdefault(row.parent, []).append(row.behaviour_reason)
		for row in rows:
			row["reasons"] = by_parent.get(row.name, [])
			row["bucket"] = bucket_for_category(row.category)

	return {"mistakes": rows}


def _editable(record):
	_guard("write")
	doc = frappe.get_doc(DOCTYPE, record)
	return doc


@frappe.whitelist()
def record_call(
	record, spoken_to=None, spoken_to_name=None, called_on=None, called_by=None, call_notes=None
):
	"""Level 1: log the call home."""
	doc = _editable(record)
	doc.call_done = 1
	doc.spoken_to = spoken_to
	doc.spoken_to_name = spoken_to_name
	doc.called_on = called_on or now_datetime()
	doc.called_by = called_by
	doc.call_notes = call_notes
	doc.save(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def record_meeting(
	record,
	parents_informed=None,
	meeting_done=None,
	met_staff=None,
	meeting_on=None,
	meeting_notes=None,
):
	"""Level 2: parents informed, and the meeting that followed."""
	doc = _editable(record)
	doc.parents_informed = cint(parents_informed)
	doc.meeting_done = cint(meeting_done)
	doc.met_staff = met_staff
	if meeting_on:
		doc.meeting_on = meeting_on
	doc.meeting_notes = meeting_notes
	doc.save(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def attach_meeting_photo(record, file_url):
	"""Point the record at a photo already uploaded through /api/method/upload_file."""
	doc = _editable(record)

	# Only a file that really exists, and really belongs to this record, may be
	# pinned to it -- the URL arrives from the browser.
	owner_doctype, owner_name = frappe.db.get_value(
		"File", {"file_url": file_url}, ["attached_to_doctype", "attached_to_name"]
	) or (None, None)

	if owner_doctype and (owner_doctype != DOCTYPE or owner_name != doc.name):
		frappe.throw(frappe._("That file belongs to another document."))
	if not frappe.db.exists("File", {"file_url": file_url}):
		frappe.throw(frappe._("Upload the photo first."))

	doc.meeting_photo = file_url
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "meeting_photo": doc.meeting_photo}


@frappe.whitelist()
def save_category_review(record, rows):
	"""Level 3: the Test / Study / Behaviour review for the month."""
	doc = _editable(record)

	if isinstance(rows, str):
		rows = json.loads(rows)

	entered = {row.get("category"): row for row in (rows or [])}
	for row in doc.category_breakdown or []:
		incoming = entered.get(row.category)
		if not incoming:
			continue
		row.what_happened = incoming.get("what_happened")
		row.action_taken = incoming.get("action_taken")
		row.reviewed = cint(incoming.get("reviewed"))

	doc.save(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def close_record(record, closure_notes=None):
	"""Take it off the list. Refused while the level's actions are unfinished --
	the controller says exactly what is missing."""
	doc = _editable(record)
	doc.closure_notes = closure_notes
	doc.status = "Closed"
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def reopen_record(record):
	doc = _editable(record)
	doc.status = "Open"
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def rebuild_month(month=None, standard=None):
	"""Recompute every record for a month from the tracker."""
	_guard("write")
	return sync_month(_resolve_month(month), standard)
