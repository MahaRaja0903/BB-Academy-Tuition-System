"""Whitelisted API behind the Student Performance Manager PWA.

Deliberately shaped like bb_academy/attendance.py — same Standard / Batch /
Gender / date filters, same holiday short-circuit, same "one call loads the
whole screen" payload — so the two pages behave identically to the teacher.

The one structural difference: performance is graded per *category*
(Study, Test, Maths Test, Behaviour), and only students the attendance register
already marked Present that day are listed.
"""

import json

import frappe
from frappe.utils import cint, flt, get_first_day, get_last_day, getdate, today

from bb_tution_management.bb_academy.attendance import get_holiday_details
from bb_tution_management.bb_academy.performance_config import (
	CATEGORIES,
	CATEGORY_RESULTS,
	LOW_RESULTS,
	PRESENT_STATUSES,
	REASON_REQUIRED_RESULTS,
	category_config,
	derive_test_result,
	slug,
)

SESSION_FIELDS = (
	"subject",
	"lesson",
	"portion",
	"total_questions",
	"total_marks",
	"pass_marks",
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _validate_category(category):
	if category not in CATEGORIES:
		frappe.throw(
			f"Invalid category: {category}. Must be one of {', '.join(CATEGORIES)}.",
			title="Invalid Category",
		)


def _validate_result(category, result):
	allowed = CATEGORY_RESULTS[category]
	if result not in allowed:
		frappe.throw(
			f"{result or 'No result'} is not a valid {category} result. "
			f"Choose one of {', '.join(allowed)}.",
			title="Invalid Result",
		)


def _parse_list(value):
	"""Accept a JSON string (what frappe-ui sends) or an already-decoded list."""
	if not value:
		return []
	if isinstance(value, str):
		value = json.loads(value)
	if not isinstance(value, (list, tuple)):
		frappe.throw("Expected a list of values.")
	return [v for v in value if v]


def _session_name(performance_date, standard, batch, category):
	return "SPS-{date}-{standard}-{batch}-{category}".format(
		date=getdate(performance_date),
		standard=slug(standard),
		batch=slug(batch),
		category=slug(category),
	)


def _get_session(performance_date, standard, batch, category):
	name = _session_name(performance_date, standard, batch, category)
	if not frappe.db.exists("Student Performance Session", name):
		return None
	return frappe.db.get_value(
		"Student Performance Session",
		name,
		["name", "date", "standard", "batch", "category", *SESSION_FIELDS],
		as_dict=True,
	)


def _guard_writable(performance_date, standard, batch):
	"""Everything the save paths must agree on before touching a row."""
	if not frappe.has_permission("Student Performance Tracker", "write"):
		frappe.throw("No permission to write performance records")

	if getdate(performance_date) > getdate(today()):
		frappe.throw("Cannot record performance for future dates")

	holiday = get_holiday_details(performance_date, standard, batch)
	if holiday:
		frappe.throw("Cannot record performance on a holiday")


def _is_present(student, performance_date):
	status = frappe.db.get_value(
		"Student Attendance",
		{"student": student, "attendance_date": getdate(performance_date)},
		"status",
	)
	return status in PRESENT_STATUSES


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_performance_meta():
	"""Category option lists, so the PWA never drifts from the server's rules."""
	return {
		"categories": [
			{
				"name": category,
				"results": CATEGORY_RESULTS[category],
				**category_config(category),
			}
			for category in CATEGORIES
		],
		"reason_required_results": REASON_REQUIRED_RESULTS,
		"present_statuses": PRESENT_STATUSES,
	}


@frappe.whitelist()
def get_behaviour_reasons():
	"""The Behaviour Reason master list, minus anything switched off."""
	if not frappe.has_permission("Behaviour Reason", "read"):
		return []

	return frappe.get_all(
		"Behaviour Reason",
		filters={"disabled": 0},
		fields=["name", "reason_name", "severity"],
		order_by="reason_name asc",
		limit_page_length=0,
	)


@frappe.whitelist()
def get_performance_students(standard, batch, category, performance_date, gender=None):
	if not frappe.has_permission("Student Performance Tracker", "read"):
		frappe.throw("No permission to read performance records")

	_validate_category(category)
	date_obj = getdate(performance_date)

	holiday = get_holiday_details(performance_date, standard, batch)
	if holiday:
		return {
			"holiday": holiday,
			"students": [],
			"summary": {},
			"session": None,
			"total_students": 0,
			"attendance_marked": 0,
		}

	params = {
		"standard": standard,
		"batch": batch,
		"date": date_obj,
		"gender": gender,
		"present": tuple(PRESENT_STATUSES),
	}
	gender_filter = " AND s.gender = %(gender)s" if gender else ""

	# The batch a student is counted under is the temporary attendance_batch when
	# one is set, exactly as the attendance register resolves it.
	roster_filter = f"""
		s.status = 'Active'
		AND s.standard = %(standard)s
		AND (
			(IFNULL(s.attendance_batch_set, 0) = 1 AND s.attendance_batch = %(batch)s)
			OR (IFNULL(s.attendance_batch_set, 0) = 0 AND s.current_batch = %(batch)s)
		)
		AND s.admission_date <= %(date)s
		{gender_filter}
	"""

	# Two counts the empty state needs to tell "attendance not taken yet" apart
	# from "attendance taken, nobody was present".
	total_students = frappe.db.sql(
		f"SELECT COUNT(s.name) FROM `tabStudent` s WHERE {roster_filter}", params
	)[0][0]

	attendance_marked = frappe.db.sql(
		f"""
		SELECT COUNT(a.name)
		FROM `tabStudent` s
		INNER JOIN `tabStudent Attendance` a
			ON a.student = s.name AND a.attendance_date = %(date)s
		WHERE {roster_filter}
		""",
		params,
	)[0][0]

	students = frappe.db.sql(
		f"""
		SELECT
			s.name, s.student_name, s.gender, s.image, s.admission_date,
			s.date_of_birth, s.attendance_batch_set, s.current_batch,
			a.status AS attendance_status
		FROM `tabStudent` s
		INNER JOIN `tabStudent Attendance` a
			ON a.student = s.name AND a.attendance_date = %(date)s
		WHERE {roster_filter}
			AND a.status IN %(present)s
		ORDER BY TRIM(SUBSTRING_INDEX(s.student_name, '.', -1)) ASC
		""",
		params,
		as_dict=True,
	)

	session = _get_session(date_obj, standard, batch, category)
	cfg = category_config(category)

	summary = {result: 0 for result in CATEGORY_RESULTS[category]}
	summary["pending"] = 0
	summary["total"] = len(students)

	if not students:
		return {
			"holiday": None,
			"students": [],
			"summary": summary,
			"session": session,
			"category": category,
			"config": cfg,
			"results": CATEGORY_RESULTS[category],
			"total_students": total_students,
			"attendance_marked": attendance_marked,
		}

	student_ids = [s.name for s in students]

	records = frappe.db.sql(
		"""
		SELECT
			`name`, `student`, `result`, `subject`, `lesson`, `portion`,
			`total_questions`, `total_marks`, `pass_marks`, `marks_obtained`, `remarks`
		FROM `tabStudent Performance Tracker`
		WHERE date = %(date)s AND category = %(category)s AND student IN %(students)s
		""",
		{"date": date_obj, "category": category, "students": tuple(student_ids)},
		as_dict=True,
	)
	record_map = {r.student: r for r in records}

	reason_map = {}
	if record_map:
		reason_rows = frappe.db.sql(
			"""
			SELECT parent, behaviour_reason
			FROM `tabStudent Behaviour Reason Item`
			WHERE parenttype = 'Student Performance Tracker' AND parent IN %(parents)s
			ORDER BY idx ASC
			""",
			{"parents": tuple(r.name for r in records)},
			as_dict=True,
		)
		for row in reason_rows:
			reason_map.setdefault(row.parent, []).append(row.behaviour_reason)

	# Month-to-date count of the grades that count against a student, so the row
	# carries the same "how often has this happened" chip the attendance page has.
	monthly = frappe.db.sql(
		"""
		SELECT student,
			SUM(CASE WHEN result IN %(low)s THEN 1 ELSE 0 END) AS low_count,
			COUNT(name) AS graded_count
		FROM `tabStudent Performance Tracker`
		WHERE date BETWEEN %(first_day)s AND %(last_day)s
			AND category = %(category)s
			AND student IN %(students)s
		GROUP BY student
		""",
		{
			"first_day": get_first_day(date_obj),
			"last_day": get_last_day(date_obj),
			"category": category,
			"students": tuple(student_ids),
			"low": tuple(LOW_RESULTS),
		},
		as_dict=True,
	)
	monthly_map = {m.student: m for m in monthly}

	result_students = []
	for s in students:
		record = record_map.get(s.name)
		stats = monthly_map.get(s.name)

		if record and record.result in summary:
			summary[record.result] += 1
		else:
			summary["pending"] += 1

		is_birthday = bool(
			s.date_of_birth
			and s.date_of_birth.month == date_obj.month
			and s.date_of_birth.day == date_obj.day
		)

		result_students.append(
			{
				"student_id": s.name,
				"student_name": s.student_name,
				"gender": s.gender,
				"image": s.image or "",
				"attendance_status": s.attendance_status,
				"is_birthday": is_birthday,
				"is_temporary": bool(s.attendance_batch_set == 1 and s.current_batch != batch),
				"original_batch": s.current_batch,
				"result": record.result if record else None,
				"marks_obtained": flt(record.marks_obtained) if record else None,
				"subject": (record.subject if record else None) or (session.subject if session else None),
				"lesson": (record.lesson if record else None) or (session.lesson if session else None),
				"portion": (record.portion if record else None) or (session.portion if session else None),
				"total_questions": cint(record.total_questions)
				if record
				else cint(session.total_questions if session else 0),
				"total_marks": flt(record.total_marks) if record else flt(session.total_marks if session else 0),
				"pass_marks": flt(record.pass_marks) if record else flt(session.pass_marks if session else 0),
				"behaviour_reasons": reason_map.get(record.name, []) if record else [],
				"remarks": (record.remarks if record else "") or "",
				"monthly_low": cint(stats.low_count) if stats else 0,
				"monthly_graded": cint(stats.graded_count) if stats else 0,
			}
		)

	return {
		"holiday": None,
		"students": result_students,
		"summary": summary,
		"session": session,
		"category": category,
		"config": cfg,
		"results": CATEGORY_RESULTS[category],
		"total_students": total_students,
		"attendance_marked": attendance_marked,
	}


# ---------------------------------------------------------------------------
# write — batch setup
# ---------------------------------------------------------------------------


@frappe.whitelist()
def save_performance_session(
	standard,
	batch,
	category,
	performance_date,
	subject=None,
	lesson=None,
	portion=None,
	total_questions=None,
	total_marks=None,
	pass_marks=None,
	apply_to_all=0,
):
	"""Store the setup that every student of this batch inherits for the day.

	`apply_to_all` pushes the new setup onto the rows already graded today —
	without it, only rows saved from now on pick it up.
	"""
	if not frappe.has_permission("Student Performance Session", "create"):
		frappe.throw("No permission to save the performance setup")

	_validate_category(category)
	_guard_writable(performance_date, standard, batch)

	date_obj = getdate(performance_date)
	values = {
		"subject": subject,
		"lesson": lesson,
		"portion": portion,
		"total_questions": cint(total_questions),
		"total_marks": flt(total_marks),
		"pass_marks": flt(pass_marks),
	}

	name = _session_name(date_obj, standard, batch, category)
	if frappe.db.exists("Student Performance Session", name):
		doc = frappe.get_doc("Student Performance Session", name)
	else:
		doc = frappe.new_doc("Student Performance Session")
		doc.date = date_obj
		doc.standard = standard
		doc.batch = batch
		doc.category = category

	doc.update(values)
	doc.save()

	updated = 0
	if cint(apply_to_all):
		updated = _apply_session_to_students(doc)

	return {
		"status": "success",
		"session": {"name": doc.name, **{field: doc.get(field) for field in SESSION_FIELDS}},
		"updated_students": updated,
	}


def _apply_session_to_students(session):
	"""Re-stamp today's already-graded rows with the batch setup.

	Marks above a newly lowered Total Marks are clamped rather than rejected —
	aborting the whole apply because one student's old score no longer fits
	would leave the batch half-updated.
	"""
	cfg = category_config(session.category)

	names = frappe.get_all(
		"Student Performance Tracker",
		filters={
			"date": session.date,
			"category": session.category,
			"standard": session.standard,
			"batch": session.batch,
		},
		pluck="name",
	)

	for name in names:
		doc = frappe.get_doc("Student Performance Tracker", name)
		doc.session = session.name

		if cfg["uses_syllabus"]:
			doc.subject = session.subject
			doc.lesson = session.lesson
			doc.portion = session.portion
		if cfg["uses_questions"]:
			doc.total_questions = session.total_questions
		if cfg["uses_marks"]:
			doc.total_marks = session.total_marks
			doc.pass_marks = session.pass_marks
			if session.total_marks and flt(doc.marks_obtained) > flt(session.total_marks):
				doc.marks_obtained = session.total_marks
			# Only re-grade rows that actually carry marks. A row the teacher
			# graded by hand without entering a score must keep that grade —
			# deriving from a blank score would flip every one of them to Fail.
			if flt(doc.marks_obtained):
				derived = derive_test_result(doc.marks_obtained, doc.total_marks, doc.pass_marks)
				if derived:
					doc.result = derived

		doc.save()

	return len(names)


@frappe.whitelist()
def clear_performance_session(standard, batch, category, performance_date):
	"""Delete the batch setup for a day. The graded rows keep their own copy."""
	if not frappe.has_permission("Student Performance Session", "delete"):
		frappe.throw("No permission to clear the performance setup")

	_validate_category(category)
	name = _session_name(performance_date, standard, batch, category)
	if frappe.db.exists("Student Performance Session", name):
		frappe.delete_doc("Student Performance Session", name)

	return {"status": "success"}


# ---------------------------------------------------------------------------
# write — per student
# ---------------------------------------------------------------------------


def _apply_values(doc, category, session, values):
	"""Write one payload onto a tracker doc, defaulting from the batch setup."""
	cfg = category_config(category)

	def pick(field):
		"""Explicit value wins, then whatever this row already holds, then the
		batch setup.

		The middle step is what makes a per-student override stick: re-tapping a
		grade button sends no subject/lesson/portion, and falling straight
		through to the batch setup would silently undo the manual change.
		"""
		if values.get(field) not in (None, ""):
			return values[field]
		current = doc.get(field)
		if current not in (None, "", 0):
			return current
		if session:
			return session.get(field)
		return None

	if cfg["uses_syllabus"]:
		doc.subject = pick("subject")
		doc.lesson = pick("lesson")
		doc.portion = pick("portion")
	if cfg["uses_questions"]:
		doc.total_questions = cint(pick("total_questions"))
	if cfg["uses_marks"]:
		doc.total_marks = flt(pick("total_marks"))
		doc.pass_marks = flt(pick("pass_marks"))
		if values.get("marks_obtained") is not None:
			doc.marks_obtained = flt(values["marks_obtained"])

	if cfg["uses_reasons"] and values.get("result") in REASON_REQUIRED_RESULTS:
		doc.behaviour_reasons = []
		for reason in _parse_list(values.get("behaviour_reasons")):
			doc.append("behaviour_reasons", {"behaviour_reason": reason})

	if values.get("remarks") is not None:
		doc.remarks = values["remarks"]

	doc.result = values["result"]
	doc.session = session.name if session else None


def _upsert_tracker(student, performance_date, category, session, values, standard=None, batch=None):
	"""Create or update the single row for this student+date+category.

	The document name is deterministic, so two teachers saving the same student
	at once collide on the primary key instead of writing two rows: the loser
	rolls back its insert and updates the winner's row.
	"""
	date_obj = getdate(performance_date)
	filters = {"student": student, "date": date_obj, "category": category}

	name = frappe.db.get_value("Student Performance Tracker", filters, "name")
	if name:
		doc = frappe.get_doc("Student Performance Tracker", name)
		_apply_values(doc, category, session, values)
		doc.save()
		return doc

	doc = frappe.new_doc("Student Performance Tracker")
	doc.student = student
	doc.date = date_obj
	doc.category = category
	doc.standard = standard
	doc.batch = batch
	_apply_values(doc, category, session, values)

	save_point = "perf_upsert"
	frappe.db.savepoint(save_point)
	try:
		doc.insert()
		return doc
	except frappe.DuplicateEntryError:
		frappe.db.rollback(save_point=save_point)

	name = frappe.db.get_value("Student Performance Tracker", filters, "name")
	if not name:
		frappe.throw(
			f"Could not save {category} performance for {student} on {date_obj}.",
			title="Performance Not Saved",
		)

	doc = frappe.get_doc("Student Performance Tracker", name)
	_apply_values(doc, category, session, values)
	doc.save()
	return doc


def _monthly_stats(student, performance_date, category):
	date_obj = getdate(performance_date)
	row = frappe.db.sql(
		"""
		SELECT
			SUM(CASE WHEN result IN %(low)s THEN 1 ELSE 0 END) AS low_count,
			COUNT(name) AS graded_count
		FROM `tabStudent Performance Tracker`
		WHERE date BETWEEN %(first_day)s AND %(last_day)s
			AND category = %(category)s AND student = %(student)s
		""",
		{
			"first_day": get_first_day(date_obj),
			"last_day": get_last_day(date_obj),
			"category": category,
			"student": student,
			"low": tuple(LOW_RESULTS),
		},
		as_dict=True,
	)[0]

	return {"monthly_low": cint(row.low_count), "monthly_graded": cint(row.graded_count)}


@frappe.whitelist()
def save_student_performance(
	student,
	performance_date,
	category,
	result=None,
	marks_obtained=None,
	behaviour_reasons=None,
	remarks=None,
	subject=None,
	lesson=None,
	portion=None,
	total_questions=None,
	total_marks=None,
	pass_marks=None,
	standard=None,
	batch=None,
):
	_validate_category(category)

	stu = frappe.db.get_value(
		"Student",
		student,
		["name", "standard", "current_batch", "attendance_batch", "attendance_batch_set"],
		as_dict=True,
	)
	if not stu:
		frappe.throw(f"Student {student} not found")

	standard = standard or stu.standard
	batch = batch or (stu.attendance_batch if stu.attendance_batch_set else stu.current_batch)

	_guard_writable(performance_date, standard, batch)

	if not _is_present(student, performance_date):
		frappe.throw(
			f"{stu.name} is not marked Present on {getdate(performance_date)}. "
			"Mark attendance first — performance is only recorded for students who attended.",
			title="Student Not Present",
		)

	session = _get_session(performance_date, standard, batch, category)
	cfg = category_config(category)

	# Numbers arrive over HTTP as strings; a cleared input arrives as "".
	marks_obtained = flt(marks_obtained) if marks_obtained not in (None, "") else None

	# A test row saved with marks but no explicit grade is graded from the marks;
	# tapping a grade button still overrides whatever the marks imply.
	if cfg["uses_marks"] and marks_obtained is not None and not result:
		against_total = total_marks if total_marks is not None else (session.total_marks if session else 0)
		against_pass = pass_marks if pass_marks is not None else (session.pass_marks if session else 0)
		result = derive_test_result(marks_obtained, against_total, against_pass)

		if not result:
			# Nothing to grade against — say which knob is missing rather than
			# letting _validate_result complain about a blank result.
			frappe.throw(
				f"Set Total Marks for this {category} before entering a student's marks — "
				"there is nothing to grade against yet.",
				title="Total Marks Not Set",
			)

	_validate_result(category, result)

	values = {
		"result": result,
		"marks_obtained": marks_obtained,
		"behaviour_reasons": behaviour_reasons,
		"remarks": remarks,
		"subject": subject,
		"lesson": lesson,
		"portion": portion,
		"total_questions": total_questions,
		"total_marks": total_marks,
		"pass_marks": pass_marks,
	}

	doc = _upsert_tracker(student, performance_date, category, session, values, standard, batch)

	return {
		"status": "success",
		"name": doc.name,
		"result": doc.result,
		"marks_obtained": flt(doc.marks_obtained),
		"behaviour_reasons": [r.behaviour_reason for r in (doc.behaviour_reasons or [])],
		**_monthly_stats(student, performance_date, category),
	}


@frappe.whitelist()
def save_bulk_performance(
	students,
	standard,
	batch,
	performance_date,
	category,
	result,
	behaviour_reasons=None,
	marks_obtained=None,
):
	_validate_category(category)
	_validate_result(category, result)
	_guard_writable(performance_date, standard, batch)

	students = _parse_list(students)
	if not students:
		frappe.throw("No students selected")

	date_obj = getdate(performance_date)

	# One query instead of one per student: anyone missing from this set was not
	# marked Present and is skipped rather than silently graded.
	present = set(
		frappe.get_all(
			"Student Attendance",
			filters={
				"student": ["in", students],
				"attendance_date": date_obj,
				"status": ["in", PRESENT_STATUSES],
			},
			pluck="student",
		)
	)

	session = _get_session(date_obj, standard, batch, category)
	values = {
		"result": result,
		"marks_obtained": marks_obtained,
		"behaviour_reasons": behaviour_reasons,
	}

	saved, skipped = [], []
	for student in students:
		if student not in present:
			skipped.append(student)
			continue
		_upsert_tracker(student, date_obj, category, session, values, standard, batch)
		saved.append(student)

	return {"status": "success", "count": len(saved), "saved": saved, "skipped": skipped}


@frappe.whitelist()
def add_behaviour_reason(reason_name, severity="Both", description=None):
	"""Add to the Behaviour Reason master straight from the PWA.

	Teachers hit a reason the master does not cover mid-session; without this
	they would have to leave for the desk and lose the marking they were doing.
	"""
	if not frappe.has_permission("Behaviour Reason", "create"):
		frappe.throw("No permission to add a behaviour reason")

	reason_name = (reason_name or "").strip()
	if not reason_name:
		frappe.throw("Reason cannot be blank")

	if frappe.db.exists("Behaviour Reason", reason_name):
		return frappe.db.get_value(
			"Behaviour Reason", reason_name, ["name", "reason_name", "severity"], as_dict=True
		)

	doc = frappe.get_doc(
		{
			"doctype": "Behaviour Reason",
			"reason_name": reason_name,
			"severity": severity if severity in ("Both", "Bad", "Worst") else "Both",
			"description": description,
		}
	).insert()

	return {"name": doc.name, "reason_name": doc.reason_name, "severity": doc.severity}
