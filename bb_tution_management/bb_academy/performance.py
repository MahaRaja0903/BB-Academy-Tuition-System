"""Whitelisted API behind the Student Performance Manager PWA.

Deliberately shaped like bb_academy/attendance.py — same Standard / Batch /
Gender / date filters, same holiday short-circuit, same "one call loads the
whole screen" payload — so the two pages behave identically to the teacher.

The one structural difference: performance is graded per *category*
(Study, Test, the standard's subject test, Behaviour), and only students the
attendance register already marked Present that day are listed.
"""

import json

import frappe
from frappe.utils import cint, flt, get_first_day, get_last_day, getdate, today

from bb_tution_management.bb_academy.attendance import get_day_context, get_holiday_details
from bb_tution_management.bb_tution_management.doctype.lesson.lesson import (
	lesson_docname,
	lessons_for,
)
from bb_tution_management.bb_tution_management.doctype.portion.portion import (
	portions as portion_master,
)
from bb_tution_management.bb_tution_management.doctype.subject.subject import (
	subjects_for_standard,
)
from bb_tution_management.bb_academy.performance_config import (
	CATEGORIES,
	CATEGORY_RESULTS,
	LOW_RESULTS,
	PRESENT_STATUSES,
	REASON_REQUIRED_RESULTS,
	SKIP_RESULT,
	categories_for_standard,
	category_config,
	default_pass_marks,
	derive_test_result,
	slug,
	test_category_for_standard,
)

# The setup fields that live directly on the session row. `lessons` and
# `portions` are child tables and are read and written separately.
SESSION_FIELDS = (
	"subject",
	"total_questions",
	"total_marks",
	"pass_marks",
)

LESSON_PARENTFIELD = "lessons"
PORTION_PARENTFIELD = "portions"


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


def _validate_subject(subject, standard):
	"""Keep the PWA honest about the Subject master the dropdown is built from."""
	if not subject:
		return

	if not frappe.db.exists("Subject", subject):
		frappe.throw(f"{subject} is not in the Subject master.", title="Unknown Subject")

	if standard and subject not in subjects_for_standard(standard):
		frappe.throw(
			f"{subject} is not offered for {standard}. "
			f"Add {standard} to the subject's Standard Applicable list first.",
			title="Subject Not Offered",
		)


def _validate_lessons(names, standard, subject):
	"""Every lesson must belong to the standard and subject being graded —
	otherwise a stale pick left over from a subject switch would be saved
	silently. Duplicates are rejected here rather than stored twice."""
	if not names:
		return

	seen = set()
	for name in names:
		if name in seen:
			frappe.throw(f"{name} is picked twice.", title="Duplicate Lesson")
		seen.add(name)

	rows = {
		r.name: r
		for r in frappe.get_all(
			"Lesson",
			filters={"name": ["in", list(seen)]},
			fields=["name", "standard", "subject"],
		)
	}

	for name in names:
		row = rows.get(name)
		if not row:
			frappe.throw(f"{name} is not in the Lesson master.", title="Unknown Lesson")

		if standard and row.standard != standard:
			frappe.throw(f"{name} is not mapped to {standard}.", title="Lesson Not Mapped")
		if subject and row.subject != subject:
			frappe.throw(f"{name} is not mapped to {subject}.", title="Lesson Not Mapped")


def _validate_portions(names):
	unknown = [p for p in names if not frappe.db.exists("Portion", p)]
	if unknown:
		frappe.throw(
			f"{', '.join(unknown)} is not in the Portion master.", title="Unknown Portion"
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


def _set_lessons(doc, names):
	doc.set(LESSON_PARENTFIELD, [])
	for name in names:
		doc.append(LESSON_PARENTFIELD, {"lesson": name})


def _lessons_of(doctype, parents):
	"""parent name -> its lesson list, in the order they were picked."""
	if not parents:
		return {}

	rows = frappe.db.sql(
		"""
		SELECT `parent`, `lesson`
		FROM `tabLesson Item`
		WHERE parenttype = %(doctype)s AND parentfield = %(parentfield)s AND parent IN %(parents)s
		ORDER BY idx ASC
		""",
		{
			"doctype": doctype,
			"parentfield": LESSON_PARENTFIELD,
			"parents": tuple(parents),
		},
		as_dict=True,
	)

	result = {}
	for row in rows:
		result.setdefault(row.parent, []).append(row.lesson)
	return result


def _set_portions(doc, names):
	doc.set(PORTION_PARENTFIELD, [])
	for name in names:
		doc.append(PORTION_PARENTFIELD, {"portion": name})


def _portions_of(doctype, parents):
	"""parent name -> its portion list, in the order they were picked."""
	if not parents:
		return {}

	# `portion` is a reserved word in MariaDB (application-time periods), so the
	# column has to be quoted even in a plain SELECT.
	rows = frappe.db.sql(
		"""
		SELECT `parent`, `portion`
		FROM `tabPortion Item`
		WHERE parenttype = %(doctype)s AND parentfield = %(parentfield)s AND parent IN %(parents)s
		ORDER BY idx ASC
		""",
		{
			"doctype": doctype,
			"parentfield": PORTION_PARENTFIELD,
			"parents": tuple(parents),
		},
		as_dict=True,
	)

	result = {}
	for row in rows:
		result.setdefault(row.parent, []).append(row.portion)
	return result


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

	session = frappe.db.get_value(
		"Student Performance Session",
		name,
		["name", "date", "standard", "batch", "category", *SESSION_FIELDS],
		as_dict=True,
	)
	session["lessons"] = _lessons_of("Student Performance Session", [name]).get(name, [])
	session["portions"] = _portions_of("Student Performance Session", [name]).get(name, [])
	return session


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


def _blank_monthly_counts(category):
	return {result: 0 for result in CATEGORY_RESULTS[category]}


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_performance_meta(standard=None):
	"""Category option lists, so the PWA never drifts from the server's rules.

	`standard` narrows the subject test to the one that standard actually sits —
	Accounts Test for Commerce, Maths Test for everyone else.
	"""
	names = categories_for_standard(standard) if standard else CATEGORIES

	return {
		"categories": [
			{
				"name": category,
				"results": CATEGORY_RESULTS[category],
				**category_config(category),
			}
			for category in names
		],
		"subject_test": test_category_for_standard(standard) if standard else None,
		"reason_required_results": REASON_REQUIRED_RESULTS,
		"present_statuses": PRESENT_STATUSES,
		"skip_result": SKIP_RESULT,
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
def get_subjects(standard=None):
	"""Subjects the standard is taught, for the Subject dropdown on the PWA."""
	if not frappe.has_permission("Subject", "read"):
		return []

	return subjects_for_standard(standard)


@frappe.whitelist()
def get_lessons(standard=None, subject=None, include=None, txt=None):
	"""Lessons mapped to this standard + subject, for the Lesson picker.

	`include` is the list already picked on the record, so a lesson that has
	since been disabled still comes back and keeps its chip labelled.
	"""
	if not frappe.has_permission("Lesson", "read"):
		return []
	if not standard or not subject:
		return []

	if include and isinstance(include, str) and include.strip().startswith("["):
		include = _parse_list(include)

	return lessons_for(standard, subject, txt=txt, include=include)


@frappe.whitelist()
def get_portions(include=None):
	"""The Portion master — the same 1M / 2M / 5M list for every standard."""
	if not frappe.has_permission("Portion", "read"):
		return []

	return portion_master(include=_parse_list(include))


@frappe.whitelist()
def get_performance_students(standard, batch, category, performance_date, gender=None):
	if not frappe.has_permission("Student Performance Tracker", "read"):
		frappe.throw("No permission to read performance records")

	_validate_category(category)
	date_obj = getdate(performance_date)

	# A Special Class Day cancels the holiday for this scope, so the day then
	# loads and grades exactly like an ordinary one.
	day = get_day_context(date_obj, standard, batch)
	if day["holiday"]:
		return {
			"holiday": day["holiday"],
			"special_class": None,
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
			"special_class": day["special_class"],
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
			`name`, `student`, `result`, `skipped`, `subject`,
			`total_questions`, `total_marks`, `pass_marks`, `marks_obtained`, `remarks`
		FROM `tabStudent Performance Tracker`
		WHERE date = %(date)s AND category = %(category)s AND student IN %(students)s
		""",
		{"date": date_obj, "category": category, "students": tuple(student_ids)},
		as_dict=True,
	)
	record_map = {r.student: r for r in records}
	record_names = [r.name for r in records]

	portion_map = _portions_of("Student Performance Tracker", record_names)
	row_lesson_map = _lessons_of("Student Performance Tracker", record_names)
	lesson_titles = _lesson_titles(
		[name for names in row_lesson_map.values() for name in names]
		+ (list(session["lessons"]) if session else [])
	)

	reason_map = {}
	if record_names:
		reason_rows = frappe.db.sql(
			"""
			SELECT parent, behaviour_reason
			FROM `tabStudent Behaviour Reason Item`
			WHERE parenttype = 'Student Performance Tracker' AND parent IN %(parents)s
			ORDER BY idx ASC
			""",
			{"parents": tuple(record_names)},
			as_dict=True,
		)
		for row in reason_rows:
			reason_map.setdefault(row.parent, []).append(row.behaviour_reason)

	# Month-to-date tally per grade, so each row can carry "Full Mark 4 · Fail 1"
	# instead of one opaque concern count.
	monthly = frappe.db.sql(
		"""
		SELECT student, result, COUNT(name) AS entries
		FROM `tabStudent Performance Tracker`
		WHERE date BETWEEN %(first_day)s AND %(last_day)s
			AND category = %(category)s
			AND student IN %(students)s
		GROUP BY student, result
		""",
		{
			"first_day": get_first_day(date_obj),
			"last_day": get_last_day(date_obj),
			"category": category,
			"students": tuple(student_ids),
		},
		as_dict=True,
	)

	monthly_map = {}
	for row in monthly:
		counts = monthly_map.setdefault(row.student, _blank_monthly_counts(category))
		if row.result in counts:
			counts[row.result] += cint(row.entries)

	result_students = []
	for s in students:
		record = record_map.get(s.name)
		counts = monthly_map.get(s.name) or _blank_monthly_counts(category)

		if record and record.result in summary:
			summary[record.result] += 1
		else:
			summary["pending"] += 1

		is_birthday = bool(
			s.date_of_birth
			and s.date_of_birth.month == date_obj.month
			and s.date_of_birth.day == date_obj.day
		)

		row_lessons = row_lesson_map.get(record.name) if record else None
		if not row_lessons:
			row_lessons = list(session["lessons"]) if session else []
		row_portions = portion_map.get(record.name) if record else None
		if not row_portions:
			row_portions = list(session["portions"]) if session else []

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
				"skipped": cint(record.skipped) if record else 0,
				"marks_obtained": flt(record.marks_obtained) if record else None,
				"subject": (record.subject if record else None) or (session.subject if session else None),
				"lessons": row_lessons,
				"lesson_titles": [lesson_titles.get(n, n) for n in row_lessons],
				"portions": row_portions,
				"total_questions": cint(record.total_questions)
				if record
				else cint(session.total_questions if session else 0),
				"total_marks": flt(record.total_marks) if record else flt(session.total_marks if session else 0),
				"pass_marks": flt(record.pass_marks) if record else flt(session.pass_marks if session else 0),
				"behaviour_reasons": reason_map.get(record.name, []) if record else [],
				"remarks": (record.remarks if record else "") or "",
				"monthly_counts": counts,
				"monthly_low": sum(counts.get(r, 0) for r in LOW_RESULTS),
				"monthly_graded": sum(counts.values()),
			}
		)

	return {
		"holiday": None,
		"special_class": day["special_class"],
		"students": result_students,
		"summary": summary,
		"session": session,
		"category": category,
		"config": cfg,
		"results": CATEGORY_RESULTS[category],
		"total_students": total_students,
		"attendance_marked": attendance_marked,
	}


def _lesson_titles(names):
	"""Lesson docname -> the bare lesson title.

	Lesson names carry their subject and standard so they stay unique; the PWA
	shows only the title, which is all the teacher needs in a crowded row.
	"""
	names = [n for n in set(names) if n]
	if not names:
		return {}

	rows = frappe.get_all(
		"Lesson", filters={"name": ["in", names]}, fields=["name", "lesson_name"]
	)
	return {r.name: r.lesson_name for r in rows}


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
	lessons=None,
	portions=None,
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
	_validate_subject(subject, standard)

	lesson_names = _parse_list(lessons)
	_validate_lessons(lesson_names, standard, subject)

	portion_names = _parse_list(portions)
	_validate_portions(portion_names)

	date_obj = getdate(performance_date)
	total_marks = flt(total_marks)
	# Half the paper passes unless the teacher typed their own pass mark.
	pass_marks = flt(pass_marks) if pass_marks not in (None, "") else 0
	if total_marks and not pass_marks:
		pass_marks = default_pass_marks(total_marks)

	values = {
		"subject": subject,
		"total_questions": cint(total_questions),
		"total_marks": total_marks,
		"pass_marks": pass_marks,
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
	_set_lessons(doc, lesson_names)
	_set_portions(doc, portion_names)
	doc.save()

	updated = 0
	if cint(apply_to_all):
		updated = _apply_session_to_students(doc)

	return {
		"status": "success",
		"session": {
			"name": doc.name,
			**{field: doc.get(field) for field in SESSION_FIELDS},
			"lessons": [row.lesson for row in (doc.lessons or [])],
			"portions": [row.portion for row in (doc.portions or [])],
		},
		"updated_students": updated,
	}


def _apply_session_to_students(session):
	"""Re-stamp today's already-graded rows with the batch setup.

	Marks above a newly lowered Total Marks are clamped rather than rejected —
	aborting the whole apply because one student's old score no longer fits
	would leave the batch half-updated.
	"""
	cfg = category_config(session.category)
	session_lessons = [row.lesson for row in (session.lessons or [])]
	session_portions = [row.portion for row in (session.portions or [])]

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
			_set_lessons(doc, session_lessons)
			_set_portions(doc, session_portions)
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
			# A skipped student is left alone: they never sat the paper.
			if flt(doc.marks_obtained) and not doc.skipped:
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
		grade button sends no subject/lessons/portions, and falling straight
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

		# Lessons and portions follow the same precedence, but a child table
		# needs the "was it sent at all" test doing by hand — an empty list is a
		# real instruction to clear what the row holds.
		if values.get("lessons") is not None:
			_set_lessons(doc, _parse_list(values["lessons"]))
		elif not doc.get(LESSON_PARENTFIELD) and session:
			_set_lessons(doc, session.get("lessons") or [])

		if values.get("portions") is not None:
			_set_portions(doc, _parse_list(values["portions"]))
		elif not doc.get(PORTION_PARENTFIELD) and session:
			_set_portions(doc, session.get("portions") or [])

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
	doc.skipped = 1 if values["result"] == SKIP_RESULT else 0
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
	"""This month's tally per grade for one student, for the row's stat chips."""
	date_obj = getdate(performance_date)
	rows = frappe.db.sql(
		"""
		SELECT result, COUNT(name) AS entries
		FROM `tabStudent Performance Tracker`
		WHERE date BETWEEN %(first_day)s AND %(last_day)s
			AND category = %(category)s AND student = %(student)s
		GROUP BY result
		""",
		{
			"first_day": get_first_day(date_obj),
			"last_day": get_last_day(date_obj),
			"category": category,
			"student": student,
		},
		as_dict=True,
	)

	counts = _blank_monthly_counts(category)
	for row in rows:
		if row.result in counts:
			counts[row.result] += cint(row.entries)

	return {
		"monthly_counts": counts,
		"monthly_low": sum(counts.get(r, 0) for r in LOW_RESULTS),
		"monthly_graded": sum(counts.values()),
	}


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
	lessons=None,
	portions=None,
	total_questions=None,
	total_marks=None,
	pass_marks=None,
	skipped=None,
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

	if cint(skipped):
		# An excused student is graded Skipped whatever else was sent, and the
		# marks are dropped — there is no paper to score.
		if not cfg["uses_skip"]:
			frappe.throw(f"{category} cannot be skipped.", title="Cannot Skip")
		result = SKIP_RESULT
		marks_obtained = None

	if result == SKIP_RESULT and not (remarks or "").strip():
		frappe.throw(
			"Remarks are required when a student skips — say why they were excused.",
			title="Remarks Required",
		)

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
	_validate_subject(subject, standard)

	lesson_names = None
	if lessons is not None:
		lesson_names = _parse_list(lessons)
		_validate_lessons(
			lesson_names, standard, subject or (session.subject if session else None)
		)

	portion_names = None
	if portions is not None:
		portion_names = _parse_list(portions)
		_validate_portions(portion_names)

	values = {
		"result": result,
		"marks_obtained": marks_obtained,
		"behaviour_reasons": behaviour_reasons,
		"remarks": remarks,
		"subject": subject,
		"lessons": lesson_names,
		"portions": portion_names,
		"total_questions": total_questions,
		"total_marks": total_marks,
		"pass_marks": pass_marks,
	}

	doc = _upsert_tracker(student, performance_date, category, session, values, standard, batch)

	return {
		"status": "success",
		"name": doc.name,
		"result": doc.result,
		"skipped": cint(doc.skipped),
		"marks_obtained": flt(doc.marks_obtained),
		"remarks": doc.remarks or "",
		"behaviour_reasons": [r.behaviour_reason for r in (doc.behaviour_reasons or [])],
		"lessons": [r.lesson for r in (doc.lessons or [])],
		"portions": [r.portion for r in (doc.portions or [])],
		**_monthly_stats(student, performance_date, category),
	}


@frappe.whitelist()
def clear_student_performance(student, performance_date, category, standard=None, batch=None):
	"""Drop one student's grade for a day, putting the row back to Pending.

	Un-ticking "Skip Test / Study" has to land somewhere, and the honest place is
	nowhere: the student is simply not graded yet.
	"""
	_validate_category(category)

	if not frappe.has_permission("Student Performance Tracker", "delete"):
		frappe.throw("No permission to clear performance records")

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

	name = frappe.db.get_value(
		"Student Performance Tracker",
		{"student": student, "date": getdate(performance_date), "category": category},
		"name",
	)
	if name:
		frappe.delete_doc("Student Performance Tracker", name, ignore_permissions=False)

	return {
		"status": "success",
		"cleared": bool(name),
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
	remarks=None,
):
	_validate_category(category)
	_validate_result(category, result)
	_guard_writable(performance_date, standard, batch)

	if result == SKIP_RESULT and not (remarks or "").strip():
		frappe.throw(
			"Remarks are required when students skip — say why they were excused.",
			title="Remarks Required",
		)

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
		"remarks": remarks,
	}

	saved, skipped_students = [], []
	for student in students:
		if student not in present:
			skipped_students.append(student)
			continue
		_upsert_tracker(student, date_obj, category, session, values, standard, batch)
		saved.append(student)

	return {
		"status": "success",
		"count": len(saved),
		"saved": saved,
		"skipped": skipped_students,
	}


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


@frappe.whitelist()
def add_lesson(lesson_name, subject, standard, lesson_order=None):
	"""Add to the Lesson master straight from the PWA, for the same reason
	`add_behaviour_reason` exists: the lesson taught today is often not in the
	master yet, and leaving the screen loses the marking in progress."""
	if not frappe.has_permission("Lesson", "create"):
		frappe.throw("No permission to add a lesson")

	lesson_name = (lesson_name or "").strip()
	if not lesson_name:
		frappe.throw("Lesson cannot be blank")
	if not subject or not standard:
		frappe.throw("Pick the Subject and Standard the lesson belongs to first.")

	_validate_subject(subject, standard)

	name = lesson_docname(lesson_name, subject, standard)
	if frappe.db.exists("Lesson", name):
		return frappe.db.get_value(
			"Lesson", name, ["name", "lesson_name", "subject", "standard"], as_dict=True
		)

	doc = frappe.get_doc(
		{
			"doctype": "Lesson",
			"lesson_name": lesson_name,
			"subject": subject,
			"standard": standard,
			"lesson_order": cint(lesson_order),
		}
	).insert()

	return {
		"name": doc.name,
		"lesson_name": doc.lesson_name,
		"subject": doc.subject,
		"standard": doc.standard,
	}


@frappe.whitelist()
def add_portion(portion_name, portion_order=None):
	"""Add to the shared Portion master from the PWA."""
	if not frappe.has_permission("Portion", "create"):
		frappe.throw("No permission to add a portion")

	portion_name = (portion_name or "").strip()
	if not portion_name:
		frappe.throw("Portion cannot be blank")

	if frappe.db.exists("Portion", portion_name):
		return frappe.db.get_value(
			"Portion", portion_name, ["name", "portion_name", "portion_order"], as_dict=True
		)

	doc = frappe.get_doc(
		{
			"doctype": "Portion",
			"portion_name": portion_name,
			"portion_order": cint(portion_order),
		}
	).insert()

	return {
		"name": doc.name,
		"portion_name": doc.portion_name,
		"portion_order": doc.portion_order,
	}
