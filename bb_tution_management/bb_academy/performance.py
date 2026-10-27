"""Whitelisted API behind the Student Performance Manager PWA.

Deliberately shaped like bb_academy/attendance.py — same Standard / Batch /
Gender / date filters, same holiday short-circuit, same "one call loads the
whole screen" payload — so the two pages behave identically to the teacher.

The one structural difference: performance is graded per *category*
(Study, Class, Test, H.W, Behaviour), and only students the attendance register
already marked Present that day are listed. Test is graded per *test*: a batch
can sit several on one day, one per Subject + Lesson + Portion combination.
"""

import json

import frappe
from frappe.utils import cint, flt, get_first_day, get_last_day, getdate, today

from bb_tution_management.bb_academy.attendance import get_day_context, get_holiday_details
from bb_tution_management.bb_academy.syllabus import (
	doc_syllabus,
	has_syllabus,
	lesson_titles,
	parse_syllabus,
	set_syllabus,
	syllabus_lessons,
	syllabus_of,
	syllabus_text,
	validate_subject,
	validate_syllabus,
)
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
	is_multi_session,
	slug,
)

# The setup fields that live directly on the session row. The syllabus
# (subjects, lessons, portions) is child tables, read and written via syllabus.py.
SESSION_FIELDS = (
	"subject",
	"test_key",
	"total_questions",
	"total_marks",
	"pass_marks",
	"no_session",
	"no_session_reason",
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


def _load_session(name):
	session = frappe.db.get_value(
		"Student Performance Session",
		name,
		["name", "date", "standard", "batch", "category", *SESSION_FIELDS],
		as_dict=True,
	)
	if not session:
		return None
	session["syllabus"] = syllabus_of("Student Performance Session", [name]).get(name, [])
	return session


def _get_session(performance_date, standard, batch, category, session_name=None):
	"""The setup row the day's grades hang off.

	Study / Class / H.W / Behaviour have one per batch per day. A Test has one
	per combination, so the caller names which (`session_name`); without one,
	only the day's "No Test" row can come back.
	"""
	if is_multi_session(category):
		if session_name:
			session = _load_session(session_name)
			if (
				not session
				or session.category != category
				or getdate(session.date) != getdate(performance_date)
				or session.standard != standard
				or session.batch != batch
			):
				frappe.throw(
					"That Test is not set for this batch on this date. Reload and pick it again.",
					title="Test Not Found",
				)
			return session

		name = _session_name(performance_date, standard, batch, category)
		if cint(frappe.db.get_value("Student Performance Session", name, "no_session")):
			return _load_session(name)
		return None

	name = _session_name(performance_date, standard, batch, category)
	if not frappe.db.exists("Student Performance Session", name):
		return None
	return _load_session(name)


def _require_test(session, category):
	"""A Test grade must belong to one Test — the combination is what it scored."""
	if is_multi_session(category) and (not session or cint(session.get("no_session"))):
		frappe.throw(
			"Add the Test first — pick its Subject, Lesson and Portion — then grade it.",
			title="Pick a Test",
		)


def _row_filters(student, performance_date, category, session):
	"""How one student's row for this category is found: by date for the
	once-a-day categories, by the Test it belongs to for Test."""
	if is_multi_session(category):
		return {"student": student, "category": category, "session": session.name if session else ""}
	return {"student": student, "date": getdate(performance_date), "category": category}


def _list_tests(performance_date, standard, batch, category="Test"):
	"""Every Test set for this batch on this date, oldest first, with how many
	students each has graded so far."""
	names = frappe.get_all(
		"Student Performance Session",
		filters={
			"date": getdate(performance_date),
			"standard": standard,
			"batch": batch,
			"category": category,
			"no_session": 0,
		},
		order_by="creation asc",
		pluck="name",
	)
	if not names:
		return []

	syllabus = syllabus_of("Student Performance Session", names)
	titles = lesson_titles(
		[lesson for blocks in syllabus.values() for lesson in syllabus_lessons(blocks)]
	)
	graded = dict(
		frappe.db.sql(
			"""
			SELECT session, COUNT(name) FROM `tabStudent Performance Tracker`
			WHERE session IN %(names)s GROUP BY session
			""",
			{"names": tuple(names)},
		)
	)

	tests = []
	for name in names:
		row = frappe.db.get_value(
			"Student Performance Session",
			name,
			["name", "subject", "test_key", "total_marks", "pass_marks"],
			as_dict=True,
		)
		row["syllabus"] = syllabus.get(name, [])
		row["label"] = syllabus_text(row["syllabus"], titles) or row.subject or name
		row["graded"] = cint(graded.get(name))
		tests.append(row)
	return tests


def _session_payload(doc):
	"""The session as the PWA reads it back, the syllabus regrouped into blocks."""
	return {
		"name": doc.name,
		"date": doc.date,
		"standard": doc.standard,
		"batch": doc.batch,
		"category": doc.category,
		**{field: doc.get(field) for field in SESSION_FIELDS},
		"syllabus": doc_syllabus(doc),
	}


def _delete_no_session_row(performance_date, standard, batch, category):
	"""Adding a Test is the teacher saying a test was held after all."""
	name = _session_name(performance_date, standard, batch, category)
	if cint(frappe.db.get_value("Student Performance Session", name, "no_session")):
		frappe.delete_doc("Student Performance Session", name, ignore_permissions=True)


def _guard_session_planned(session, category, performance_date):
	"""Refuse to grade a day management planned nothing for.

	"No Test" is a statement about the whole batch, so a single grade slipping in
	afterwards would contradict the card the screen is showing everyone else.
	"""
	if session and cint(session.get("no_session")):
		frappe.throw(
			f"No {category} was planned for this batch on {getdate(performance_date)}. "
			f"Undo \"No {category}\" first if one was held after all.",
			title=f"No {category} Planned",
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


def _blank_monthly_counts(category):
	return {result: 0 for result in CATEGORY_RESULTS[category]}


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_performance_meta(standard=None):
	"""Category option lists, so the PWA never drifts from the server's rules."""
	names = categories_for_standard(standard)

	return {
		"categories": [
			{
				"name": category,
				"results": CATEGORY_RESULTS[category],
				**category_config(category),
			}
			for category in names
		],
		"reason_required_results": REASON_REQUIRED_RESULTS,
		"present_statuses": PRESENT_STATUSES,
		"skip_result": SKIP_RESULT,
	}


@frappe.whitelist()
def get_behaviour_reasons():
	"""The Behaviour Reason master list, minus anything switched off."""
	if not frappe.has_permission("Behaviour Reason", "read"):
		return []

	reasons = frappe.get_all(
		"Behaviour Reason",
		filters={"disabled": 0},
		fields=["name", "reason_name", "severity", "display_order", "description"],
		order_by="reason_name asc",
		limit_page_length=0,
	)
	# Reasons not yet given a Display Order go after the numbered ones.
	reasons.sort(key=lambda r: (not r.display_order, r.display_order or 0))
	return reasons


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
def get_performance_students(standard, batch, category, performance_date, gender=None, session_name=None):
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
			"tests": [],
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

	multi = is_multi_session(category)
	tests = _list_tests(date_obj, standard, batch, category) if multi else []
	if multi and session_name and session_name not in {t.name for t in tests}:
		# The Test was removed or edited away by someone else — fall back to
		# "pick a Test" instead of erroring the whole screen.
		session_name = None
	session = _get_session(date_obj, standard, batch, category, session_name)
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
			"tests": tests,
			"category": category,
			"config": cfg,
			"results": CATEGORY_RESULTS[category],
			"lesson_titles": lesson_titles(syllabus_lessons(session["syllabus"] if session else [])),
			"total_students": total_students,
			"attendance_marked": attendance_marked,
		}

	student_ids = [s.name for s in students]

	# A Test's rows are the ones graded against that Test; with no Test picked
	# yet there is nothing to show against.
	row_scope = "AND session = %(session)s" if multi else ""
	records = frappe.db.sql(
		f"""
		SELECT
			`name`, `student`, `result`, `skipped`, `subject`,
			`total_questions`, `total_marks`, `pass_marks`, `marks_obtained`, `remarks`
		FROM `tabStudent Performance Tracker`
		WHERE date = %(date)s AND category = %(category)s AND student IN %(students)s
			{row_scope}
		""",
		{
			"date": date_obj,
			"category": category,
			"students": tuple(student_ids),
			"session": session.name if session else "",
		},
		as_dict=True,
	)
	record_map = {r.student: r for r in records}
	record_names = [r.name for r in records]

	row_syllabus_map = syllabus_of("Student Performance Tracker", record_names)
	session_syllabus = session["syllabus"] if session else []
	titles = lesson_titles(
		[name for blocks in row_syllabus_map.values() for name in syllabus_lessons(blocks)]
		+ syllabus_lessons(session_syllabus)
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

	instead_map = _instead_entries(
		[r.student for r in records if cint(r.skipped)], date_obj, category
	)
	titles.update(
		lesson_titles(
			[
				lesson
				for entries in instead_map.values()
				for e in entries
				for lesson in syllabus_lessons(e["syllabus"])
			]
		)
	)

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

		# A row that never had its own syllabus shows what the batch was set up to cover.
		row_syllabus = row_syllabus_map.get(record.name) if record else None
		if not row_syllabus:
			row_syllabus = session_syllabus

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
				"syllabus": row_syllabus,
				"total_questions": cint(record.total_questions)
				if record
				else cint(session.total_questions if session else 0),
				"total_marks": flt(record.total_marks) if record else flt(session.total_marks if session else 0),
				"pass_marks": flt(record.pass_marks) if record else flt(session.pass_marks if session else 0),
				"behaviour_reasons": reason_map.get(record.name, []) if record else [],
				"remarks": (record.remarks if record else "") or "",
				"instead": instead_map.get(s.name, []) if record and cint(record.skipped) else [],
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
		"tests": tests,
		"category": category,
		"config": cfg,
		"results": CATEGORY_RESULTS[category],
		"lesson_titles": titles,
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
	syllabus=None,
	subject=None,
	lessons=None,
	portions=None,
	total_questions=None,
	total_marks=None,
	pass_marks=None,
	apply_to_all=0,
	session_name=None,
):
	"""Store the setup that every student of this batch inherits for the day.

	`syllabus` is one block per subject the class covered, each with its own
	lessons and portions. `apply_to_all` pushes the new setup onto the rows
	already graded today — without it, only rows saved from now on pick it up.

	For Test, each call is one test: `session_name` edits an existing one,
	leaving it out adds a new one. The same Subject + Lesson + Portion
	combination cannot be added twice for a batch on one day.
	"""
	if not frappe.has_permission("Student Performance Session", "create"):
		frappe.throw("No permission to save the performance setup")

	_validate_category(category)
	_guard_writable(performance_date, standard, batch)

	blocks = parse_syllabus(syllabus, subject, lessons, portions) or []
	validate_syllabus(blocks, standard)

	multi = is_multi_session(category)
	if multi:
		if len(blocks) > 1:
			frappe.throw(
				"A Test covers one subject. Save this one, then add another Test for the next subject.",
				title="One Subject Per Test",
			)
		if not blocks or not blocks[0]["subject"]:
			frappe.throw("Pick the Subject this Test is on.", title="Subject Required")

	date_obj = getdate(performance_date)
	total_marks = flt(total_marks)
	# Half the paper passes unless the teacher typed their own pass mark.
	pass_marks = flt(pass_marks) if pass_marks not in (None, "") else 0
	if total_marks and not pass_marks:
		pass_marks = default_pass_marks(total_marks)

	values = {
		"total_questions": cint(total_questions),
		"total_marks": total_marks,
		"pass_marks": pass_marks,
	}

	if multi:
		existing = _get_session(date_obj, standard, batch, category, session_name) if session_name else None
		name = existing.name if existing else None
		_delete_no_session_row(date_obj, standard, batch, category)
	else:
		name = _session_name(date_obj, standard, batch, category)

	if name and frappe.db.exists("Student Performance Session", name):
		doc = frappe.get_doc("Student Performance Session", name)
	else:
		doc = frappe.new_doc("Student Performance Session")
		doc.date = date_obj
		doc.standard = standard
		doc.batch = batch
		doc.category = category

	old_key = doc.get("test_key")
	doc.update(values)
	# Entering a setup is the teacher saying the session did happen, so it
	# cancels an earlier "No Study / No Test" for the day.
	doc.no_session = 0
	set_syllabus(doc, blocks)
	doc.save()

	updated = 0
	# A Test's combination is what its rows were graded on, so editing it moves
	# every graded row with it, asked or not.
	if cint(apply_to_all) or (multi and old_key and old_key != doc.test_key):
		updated = _apply_session_to_students(doc)

	return {
		"status": "success",
		"session": _session_payload(doc),
		"updated_students": updated,
	}


def _apply_session_to_students(session):
	"""Re-stamp today's already-graded rows with the batch setup.

	Marks above a newly lowered Total Marks are clamped rather than rejected —
	aborting the whole apply because one student's old score no longer fits
	would leave the batch half-updated.
	"""
	cfg = category_config(session.category)
	session_syllabus = doc_syllabus(session)

	if is_multi_session(session.category):
		filters = {"session": session.name}
	else:
		filters = {
			"date": session.date,
			"category": session.category,
			"standard": session.standard,
			"batch": session.batch,
		}
	names = frappe.get_all("Student Performance Tracker", filters=filters, pluck="name")

	for name in names:
		doc = frappe.get_doc("Student Performance Tracker", name)
		doc.session = session.name

		if cfg["uses_syllabus"]:
			set_syllabus(doc, session_syllabus)
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
def set_no_session(standard, batch, category, performance_date, no_session=1, reason=None):
	"""Record that management planned no Study / Test for this batch on this date.

	It is the counterpart of the per-student skip: one student being excused is a
	skip, the whole batch never sitting it is a day that was never planned. The
	flag lives on the same session row the setup does, so the day carries one
	record either way.
	"""
	if not frappe.has_permission("Student Performance Session", "create"):
		frappe.throw("No permission to change the performance setup")

	_validate_category(category)
	if not category_config(category)["uses_skip"]:
		frappe.throw(f"{category} cannot be marked as not planned.", title="Cannot Skip")

	_guard_writable(performance_date, standard, batch)

	date_obj = getdate(performance_date)
	flag = cint(no_session)

	if flag:
		# Results and "nothing was planned" cannot both be true for the day.
		# Refusing is safer than deleting grades somebody already recorded.
		graded = frappe.db.count(
			"Student Performance Tracker",
			{"date": date_obj, "category": category, "standard": standard, "batch": batch},
		)
		if graded:
			frappe.throw(
				f"{graded} student(s) already have a {category} result on {date_obj}. "
				"Clear those first.",
				title=f"No {category} Not Set",
			)

	name = _session_name(date_obj, standard, batch, category)

	if is_multi_session(category):
		if not flag:
			# The "No Test" row carries nothing else, so undoing it removes it.
			_delete_no_session_row(date_obj, standard, batch, category)
			return {"status": "success", "session": None}
		# Nothing was graded (checked above), so the Tests set up for the day
		# were never held — drop them along with the flag going up.
		for test in _list_tests(date_obj, standard, batch, category):
			frappe.delete_doc("Student Performance Session", test.name)

	if frappe.db.exists("Student Performance Session", name):
		doc = frappe.get_doc("Student Performance Session", name)
	else:
		doc = frappe.new_doc("Student Performance Session")
		doc.date = date_obj
		doc.standard = standard
		doc.batch = batch
		doc.category = category

	doc.no_session = flag
	doc.no_session_reason = (reason or "").strip() if flag else None
	doc.save()

	return {"status": "success", "session": _session_payload(doc)}


@frappe.whitelist()
def clear_performance_session(standard, batch, category, performance_date, session_name=None):
	"""Delete the batch setup for a day. The graded rows keep their own copy.

	A Test with graded rows is refused instead — its rows are only findable
	through it."""
	if not frappe.has_permission("Student Performance Session", "delete"):
		frappe.throw("No permission to clear the performance setup")

	_validate_category(category)
	if is_multi_session(category):
		session = _get_session(performance_date, standard, batch, category, session_name)
		name = session.name if session else None
		if name and frappe.db.count("Student Performance Tracker", {"session": name}):
			frappe.throw(
				"Students are already graded on this Test. Clear their grades first.",
				title="Test Has Grades",
			)
	else:
		name = _session_name(performance_date, standard, batch, category)
	if name and frappe.db.exists("Student Performance Session", name):
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
		grade button sends no marks or totals, and falling straight through to
		the batch setup would silently undo the manual change.
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
		# The same precedence for the syllabus, but child tables need the "was it
		# sent at all" test doing by hand — an empty list is a real instruction to
		# clear what the row holds. Re-tapping a grade sends nothing, so a
		# per-student syllabus survives it.
		if is_multi_session(category):
			# A Test row always carries its Test's combination — that is what
			# the student was scored on.
			set_syllabus(doc, session.get("syllabus") or [])
		elif values.get("syllabus") is not None:
			set_syllabus(doc, values["syllabus"])
		elif not has_syllabus(doc) and session:
			set_syllabus(doc, session.get("syllabus") or [])

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
	"""Create or update the single row for this student+date+category (+Test).

	The document name is deterministic, so two teachers saving the same student
	at once collide on the primary key instead of writing two rows: the loser
	rolls back its insert and updates the winner's row.
	"""
	date_obj = getdate(performance_date)
	filters = _row_filters(student, date_obj, category, session)

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
	syllabus=None,
	subject=None,
	lessons=None,
	portions=None,
	total_questions=None,
	total_marks=None,
	pass_marks=None,
	skipped=None,
	standard=None,
	batch=None,
	session_name=None,
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

	session = _get_session(performance_date, standard, batch, category, session_name)
	_guard_session_planned(session, category, performance_date)
	_require_test(session, category)
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

	blocks = parse_syllabus(syllabus, subject, lessons, portions)
	if blocks is not None:
		validate_syllabus(blocks, standard)

	values = {
		"result": result,
		"marks_obtained": marks_obtained,
		"behaviour_reasons": behaviour_reasons,
		"remarks": remarks,
		"syllabus": blocks,
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
		"syllabus": doc_syllabus(doc),
		"session": doc.session,
		**_monthly_stats(student, performance_date, category),
	}


@frappe.whitelist()
def clear_student_performance(
	student, performance_date, category, standard=None, batch=None, session_name=None
):
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

	session = _get_session(performance_date, standard, batch, category, session_name)
	_require_test(session, category)
	name = frappe.db.get_value(
		"Student Performance Tracker",
		_row_filters(student, performance_date, category, session),
		"name",
	)
	if name:
		frappe.delete_doc("Student Performance Tracker", name, ignore_permissions=False)

	return {
		"status": "success",
		"cleared": bool(name),
		**_monthly_stats(student, performance_date, category),
	}


# What a skipped student can be recorded as having done instead.
INSTEAD_CATEGORIES = ["Study", "Test"]


def _instead_options(category, standard):
	"""The categories a skip of `category` can point at. Itself only when the
	day can hold several of it — a skipped Test can be another Test sat."""
	offered = categories_for_standard(standard)
	return [
		c
		for c in INSTEAD_CATEGORIES
		if c in offered and (c != category or is_multi_session(category))
	]


def _instead_remarks_prefix(category):
	"""How the row saved in place of a skipped `category` is told apart."""
	return f"In place of {category}:"


def _instead_entries(student_ids, performance_date, category):
	"""What each skipped student did in place of `category` that day — the
	Study or Test rows the skip modal saved — keyed by student."""
	if not student_ids:
		return {}
	rows = frappe.db.sql(
		"""
		SELECT `name`, `student`, `category`, `result`, `marks_obtained`, `total_marks`
		FROM `tabStudent Performance Tracker`
		WHERE date = %(date)s AND student IN %(students)s AND category IN %(categories)s
			AND IFNULL(skipped, 0) = 0 AND remarks LIKE %(prefix)s
		ORDER BY creation ASC
		""",
		{
			"date": getdate(performance_date),
			"students": tuple(student_ids),
			"categories": tuple(INSTEAD_CATEGORIES),
			"prefix": _instead_remarks_prefix(category) + "%",
		},
		as_dict=True,
	)
	syllabus = syllabus_of("Student Performance Tracker", [r.name for r in rows])
	out = {}
	for r in rows:
		out.setdefault(r.student, []).append(
			{
				"category": r.category,
				"result": r.result,
				"marks_obtained": flt(r.marks_obtained) if r.marks_obtained is not None else None,
				"total_marks": flt(r.total_marks),
				"syllabus": syllabus.get(r.name, []),
			}
		)
	return out


@frappe.whitelist()
def get_student_entry(
	student,
	performance_date,
	category,
	standard=None,
	batch=None,
	session_name=None,
	exclude_session=None,
):
	"""One student's row for a day in some other category, for the skip modal.

	Falls back to that category's batch setup, so a Test the student sat instead
	opens on the day's Total Marks rather than a blank paper. `exclude_session`
	leaves out the Test being skipped when the student sat another one.
	"""
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

	# A Test sat instead has to be one of the day's Tests — the modal lists them
	# and opens on the first unless one is picked.
	tests = []
	if is_multi_session(category):
		tests = _list_tests(performance_date, standard, batch, category)
		if exclude_session:
			tests = [t for t in tests if t.name != exclude_session]
		if session_name not in {t.name for t in tests}:
			session_name = tests[0].name if tests else None
	session = _get_session(performance_date, standard, batch, category, session_name)

	name = None
	if session or not is_multi_session(category):
		name = frappe.db.get_value(
			"Student Performance Tracker",
			_row_filters(student, performance_date, category, session),
			"name",
		)
	if name:
		doc = frappe.get_doc("Student Performance Tracker", name)
		return {
			"exists": True,
			"result": doc.result,
			"skipped": cint(doc.skipped),
			"syllabus": doc_syllabus(doc),
			"total_marks": flt(doc.total_marks),
			"pass_marks": flt(doc.pass_marks),
			"marks_obtained": flt(doc.marks_obtained),
			"no_session": cint(session.get("no_session")) if session else 0,
			"tests": tests,
			"session_name": session.name if session else None,
		}

	return {
		"exists": False,
		"result": None,
		"skipped": 0,
		"syllabus": session.get("syllabus") if session else [],
		"total_marks": flt(session.get("total_marks")) if session else 0,
		"pass_marks": flt(session.get("pass_marks")) if session else 0,
		"marks_obtained": None,
		"no_session": cint(session.get("no_session")) if session else 0,
		"tests": tests,
		"session_name": session.name if session else None,
	}


@frappe.whitelist()
def skip_student_performance(
	student,
	performance_date,
	category,
	remarks,
	syllabus=None,
	subject=None,
	lessons=None,
	portions=None,
	instead_category=None,
	instead_result=None,
	instead_marks_obtained=None,
	instead_total_marks=None,
	standard=None,
	batch=None,
	session_name=None,
	instead_session_name=None,
):
	"""Skip one student out of `category`, and optionally record what they did
	instead — a Study grade or a Test score — in that category's own row.

	Both writes share the request's transaction, so a bad Test score never
	leaves a skip behind without the entry it was meant to explain.
	"""
	res = save_student_performance(
		student,
		performance_date,
		category,
		skipped=1,
		remarks=remarks,
		syllabus=syllabus,
		subject=subject,
		lessons=lessons,
		portions=portions,
		standard=standard,
		batch=batch,
		session_name=session_name,
	)

	if not instead_category:
		return res

	standard = standard or frappe.db.get_value("Student", student, "standard")
	if instead_category not in _instead_options(category, standard):
		frappe.throw(
			f"{instead_category} cannot be recorded in place of {category}.",
			title="Invalid Choice",
		)

	if instead_category == category and instead_session_name in (None, "", session_name):
		frappe.throw(
			f"Pick another {category} — the student cannot sit the one they skipped.",
			title="Invalid Choice",
		)

	instead_cfg = category_config(instead_category)
	if instead_total_marks in (None, "") or not instead_cfg["uses_marks"]:
		instead_total_marks = None
	has_marks = instead_marks_obtained not in (None, "")
	if instead_cfg["uses_marks"]:
		if not has_marks and not instead_result:
			frappe.throw(
				f"Enter the marks {instead_category} was scored at, or pick a grade.",
				title="Marks Required",
			)
	elif not instead_result:
		frappe.throw(f"Pick a {instead_category} grade.", title="Grade Required")

	instead = save_student_performance(
		student,
		performance_date,
		instead_category,
		result=instead_result or None,
		marks_obtained=instead_marks_obtained if instead_cfg["uses_marks"] else None,
		total_marks=instead_total_marks,
		pass_marks=default_pass_marks(instead_total_marks) if instead_total_marks else None,
		remarks=f"{_instead_remarks_prefix(category)} {remarks.strip()}",
		syllabus=syllabus,
		subject=subject,
		lessons=lessons,
		portions=portions,
		standard=standard,
		batch=batch,
		session_name=instead_session_name,
	)
	res["instead"] = {
		"category": instead_category,
		"result": instead["result"],
		"marks_obtained": instead["marks_obtained"],
		"total_marks": flt(frappe.db.get_value("Student Performance Tracker", instead["name"], "total_marks")),
		"syllabus": instead["syllabus"],
	}
	return res


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
	session_name=None,
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

	session = _get_session(date_obj, standard, batch, category, session_name)
	_guard_session_planned(session, category, date_obj)
	_require_test(session, category)
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

	existing = frappe.db.get_value(
		"Behaviour Reason", {"reason_name": reason_name}, ["name", "reason_name", "severity"], as_dict=True
	)
	if existing:
		return existing

	doc = frappe.get_doc(
		{
			"doctype": "Behaviour Reason",
			"reason_name": reason_name,
			"severity": severity if severity in ("Both", "Discipline", "Critical") else "Both",
			"description": description,
		}
	).insert()

	return {"name": doc.name, "reason_name": doc.reason_name, "severity": doc.severity}


@frappe.whitelist()
def add_subject(subject_name, standard):
	"""Add a subject for this standard straight from the PWA, for the same reason
	as `add_lesson`: a class on a subject the master does not offer yet should
	not send the teacher off the screen mid-marking.

	A subject already in the master is reused — if it is not offered to this
	standard yet, the standard is added to its Standard Applicable list."""
	subject_name = (subject_name or "").strip()
	if not subject_name:
		frappe.throw("Subject cannot be blank")
	if not standard:
		frappe.throw("Pick the Standard the subject is taught in first.")

	if frappe.db.exists("Subject", subject_name):
		if subject_name in subjects_for_standard(standard):
			return subject_name
		if not frappe.has_permission("Subject", "write"):
			frappe.throw("No permission to add a subject")
		doc = frappe.get_doc("Subject", subject_name)
		doc.append("standard_applicable", {"standard": standard})
		doc.save()
		return doc.name

	if not frappe.has_permission("Subject", "create"):
		frappe.throw("No permission to add a subject")

	doc = frappe.get_doc(
		{
			"doctype": "Subject",
			"subject_name": subject_name,
			"standard_applicable": [{"standard": standard}],
		}
	).insert()

	return doc.name


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

	validate_subject(subject, standard)

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
