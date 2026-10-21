"""One call that assembles everything the Student Profile screen shows.

The screen exists to be turned around and shown to a parent across a desk, so
this module does the interpreting rather than shipping raw rows: it works out
the attendance band, the pass rates, the behaviour picture and a short list of
plain-language highlights, and the page just renders them.

Everything is scoped to a date range (the page defaults to the current month).
"""

import frappe
from frappe.utils import (
	add_days,
	cint,
	date_diff,
	flt,
	get_first_day,
	get_last_day,
	getdate,
	today,
)

from bb_tution_management.bb_academy.syllabus import (
	lesson_titles,
	syllabus_lessons,
	syllabus_of,
	syllabus_text,
)
from bb_tution_management.bb_academy.performance_config import (
	CATEGORIES,
	CATEGORY_RESULTS,
	LOW_RESULTS,
	REASON_REQUIRED_RESULTS,
	SKIP_RESULT,
	category_config,
)

# A parent meeting looks back over a term at most. Guarding the range keeps one
# mistyped date from pulling years of rows into a single payload.
MAX_RANGE_DAYS = 400

# Attendance bands, best first. `floor` is the percentage at which the band
# starts; the labels are deliberately parent-facing rather than statistical.
ATTENDANCE_BANDS = [
	(95, "excellent", "Excellent Attendance"),
	(85, "good", "Good Attendance"),
	(75, "fair", "Fair Attendance"),
	(0, "poor", "Attendance Needs Attention"),
]

STUDENT_FIELDS = [
	"name",
	"student_name",
	"admission_number",
	"image",
	"gender",
	"status",
	"date_of_birth",
	"admission_date",
	"blood_group",
	"standard",
	"current_batch",
	"attendance_batch",
	"attendance_batch_set",
	"academic_year",
	"school_name",
	"father_name",
	"father_mobile_number",
	"mother_name",
	"mother_mobile_number",
	"guardian_name",
	"guardian_mobile_number",
	"guardian_occupation",
	"relation_with_guardian",
	"preferred_mobile_number",
	"area",
	"street_name",
	"address",
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _resolve_range(from_date, to_date):
	if not from_date or not to_date:
		anchor = getdate(from_date or to_date or today())
		from_date = from_date or get_first_day(anchor)
		to_date = to_date or get_last_day(anchor)

	from_date, to_date = getdate(from_date), getdate(to_date)
	if from_date > to_date:
		frappe.throw("From Date cannot be after To Date")
	if date_diff(to_date, from_date) > MAX_RANGE_DAYS:
		frappe.throw(f"Pick a range of {MAX_RANGE_DAYS} days or less.")

	return from_date, to_date


def _band(pct):
	for floor, key, label in ATTENDANCE_BANDS:
		if pct >= floor:
			return {"key": key, "label": label}
	return {"key": "poor", "label": "Attendance Needs Attention"}


def _pct(part, whole):
	return round((part / whole) * 100, 1) if whole else 0.0


def _student_batch(student):
	return student.attendance_batch if student.attendance_batch_set else student.current_batch


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@frappe.whitelist()
def search_students(query=None, standard=None, batch=None, gender=None, limit=25):
	"""Type-ahead for the profile picker: name or ID, optionally narrowed."""
	if not frappe.has_permission("Student", "read"):
		frappe.throw("No permission to read students")

	conditions = ["s.status = 'Active'"]
	params = {"limit": cint(limit) or 25}

	if query:
		conditions.append("(s.student_name LIKE %(query)s OR s.name LIKE %(query)s)")
		params["query"] = f"%{query}%"
	if standard:
		conditions.append("s.standard = %(standard)s")
		params["standard"] = standard
	if batch:
		conditions.append(
			"""(
				(IFNULL(s.attendance_batch_set, 0) = 1 AND s.attendance_batch = %(batch)s)
				OR (IFNULL(s.attendance_batch_set, 0) = 0 AND s.current_batch = %(batch)s)
			)"""
		)
		params["batch"] = batch
	if gender:
		conditions.append("s.gender = %(gender)s")
		params["gender"] = gender

	return frappe.db.sql(
		f"""
		SELECT s.name, s.student_name, s.standard, s.current_batch, s.gender, s.image
		FROM `tabStudent` s
		WHERE {' AND '.join(conditions)}
		ORDER BY TRIM(SUBSTRING_INDEX(s.student_name, '.', -1)) ASC
		LIMIT %(limit)s
		""",
		params,
		as_dict=True,
	)


# ---------------------------------------------------------------------------
# profile
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_student_profile(student, from_date=None, to_date=None):
	if not frappe.has_permission("Student", "read"):
		frappe.throw("No permission to read students")

	from_date, to_date = _resolve_range(from_date, to_date)

	details = frappe.db.get_value("Student", student, STUDENT_FIELDS, as_dict=True)
	if not details:
		frappe.throw(f"Student {student} not found")

	batch = _student_batch(details)

	# Each section is gated on its own doctype: a user who may see students but
	# not the attendance register gets a profile with that band empty rather
	# than a permission error on the whole page.
	can_attendance = frappe.has_permission("Student Attendance", "read")
	can_performance = frappe.has_permission("Student Performance Tracker", "read")

	holidays = _get_holidays(from_date, to_date, details.standard, batch) if can_attendance else []
	attendance = (
		_get_attendance(student, from_date, to_date, holidays) if can_attendance else _empty_attendance()
	)
	performance = _get_performance(student, from_date, to_date) if can_performance else _empty_performance()
	behaviour = (
		_get_behaviour_incidents(student, from_date, to_date)
		if can_performance
		else _empty_behaviour()
	)
	tests = _get_test_breakdown(student, from_date, to_date) if can_performance else _empty_tests()

	return {
		"student": {
			**details,
			"batch": batch,
			"age": _age(details.date_of_birth),
			"years_with_us": _years_since(details.admission_date),
		},
		"range": {"from_date": from_date, "to_date": to_date},
		"attendance": attendance,
		"performance": performance,
		"behaviour": behaviour,
		"tests": tests,
		"timeline": _get_timeline(student, from_date, to_date, can_attendance, can_performance),
		"highlights": _build_highlights(details, attendance, performance, behaviour, tests),
	}


def _empty_attendance():
	return {
		"school_days": 0,
		"present": 0,
		"absent": 0,
		"late": 0,
		"early_outs": 0,
		"attended": 0,
		"percentage": 0.0,
		"band": _band(0),
		"best_streak": 0,
		"current_streak": 0,
		"holidays": [],
		"days": [],
		"monthly": [],
	}


def _empty_behaviour():
	return {
		"incidents": [],
		"reason_counts": [],
		"by_result": [
			{"result": r, "days": 0, "reasons": []} for r in REASON_REQUIRED_RESULTS
		],
	}


def _empty_tests():
	return {"failures": [], "by_subject": [], "total_failed": 0, "total_sat": 0}


def _empty_performance():
	categories = [
		{
			"name": name,
			"entries": 0,
			"concerns": 0,
			"uses_marks": category_config(name)["uses_marks"],
			"uses_reasons": category_config(name)["uses_reasons"],
			"results": [
				{"result": r, "count": 0, "is_concern": r in LOW_RESULTS} for r in CATEGORY_RESULTS[name]
			],
			"marks_obtained": 0.0,
			"total_marks": 0.0,
			"percentage": None,
			"good_percentage": 0.0,
		}
		for name in CATEGORIES
	]
	return {
		"categories": categories,
		"recorded_categories": [],
		"total_entries": 0,
		"total_concerns": 0,
	}


def _age(date_of_birth):
	if not date_of_birth:
		return None
	return max(0, int(date_diff(getdate(today()), getdate(date_of_birth)) / 365.25))


def _years_since(start):
	if not start:
		return None
	return round(date_diff(getdate(today()), getdate(start)) / 365.25, 1)


def _get_holidays(from_date, to_date, standard, batch):
	"""Holidays that applied to this student, so days off are not read as gaps."""
	rows = frappe.db.sql(
		"""
		SELECT holiday_date, holiday_type, reason, scope
		FROM `tabAttendance Holiday`
		WHERE holiday_date BETWEEN %(from_date)s AND %(to_date)s
			AND (
				scope = 'Entire School'
				OR (scope = 'Standard' AND standard = %(standard)s)
				OR (scope = 'Standard + Batch' AND standard = %(standard)s AND batch = %(batch)s)
			)
		ORDER BY holiday_date ASC
		""",
		{"from_date": from_date, "to_date": to_date, "standard": standard, "batch": batch},
		as_dict=True,
	)
	return rows


def _get_attendance(student, from_date, to_date, holidays):
	rows = frappe.db.sql(
		"""
		SELECT attendance_date, status, remarks
		FROM `tabStudent Attendance`
		WHERE student = %(student)s AND attendance_date BETWEEN %(from_date)s AND %(to_date)s
		ORDER BY attendance_date ASC
		""",
		{"student": student, "from_date": from_date, "to_date": to_date},
		as_dict=True,
	)

	counts = {"Present": 0, "Absent": 0, "Late": 0, "Early Outs": 0}
	for row in rows:
		if row.status in counts:
			counts[row.status] += 1

	marked = len(rows)
	# A late arrival is still a day attended — parents read the percentage as
	# "how often was my child here", so Late counts towards it and is called out
	# separately below.
	attended = counts["Present"] + counts["Late"] + counts["Early Outs"]
	pct = _pct(attended, marked)

	# Longest unbroken run of attended days, and the current run at the end of
	# the range — the single most encouraging number on the page.
	best_streak = current_streak = 0
	for row in rows:
		if row.status == "Absent":
			current_streak = 0
		else:
			current_streak += 1
			best_streak = max(best_streak, current_streak)

	holiday_map = {str(h.holiday_date): h for h in holidays}

	days = []
	for row in rows:
		days.append(
			{
				"date": row.attendance_date,
				"status": row.status,
				"remarks": row.remarks or "",
			}
		)
	# Student-wise holidays: one entry per day, skipping days already covered
	# by a school holiday or carrying an attendance record.
	taken = set(holiday_map) | {str(r.attendance_date) for r in rows}
	for sh in frappe.db.sql(
		"""
		SELECT from_date, to_date, reason
		FROM `tabStudent Holiday`
		WHERE student = %(student)s AND from_date <= %(to_date)s AND to_date >= %(from_date)s
		""",
		{"student": student, "from_date": from_date, "to_date": to_date},
		as_dict=True,
	):
		d = max(getdate(sh.from_date), getdate(from_date))
		end = min(getdate(sh.to_date), getdate(to_date))
		while d <= end:
			if str(d) not in taken:
				days.append({"date": d, "status": "Holiday", "remarks": f"Student Holiday — {sh.reason}"})
			d = add_days(d, 1)

	for key, holiday in holiday_map.items():
		days.append(
			{
				"date": holiday.holiday_date,
				"status": "Holiday",
				"remarks": f"{holiday.holiday_type} — {holiday.reason}",
			}
		)
	days.sort(key=lambda d: d["date"])

	return {
		"school_days": marked,
		"present": counts["Present"],
		"absent": counts["Absent"],
		"late": counts["Late"],
		"early_outs": counts["Early Outs"],
		"attended": attended,
		"percentage": pct,
		"band": _band(pct),
		"best_streak": best_streak,
		"current_streak": current_streak,
		"holidays": holidays,
		"days": days,
		"monthly": _monthly_attendance(student, from_date, to_date),
	}


def _monthly_attendance(student, from_date, to_date):
	"""Month-by-month attendance %, for the trend strip."""
	rows = frappe.db.sql(
		"""
		SELECT
			DATE_FORMAT(attendance_date, '%%Y-%%m') AS month,
			COUNT(name) AS marked,
			SUM(CASE WHEN status = 'Absent' THEN 0 ELSE 1 END) AS attended
		FROM `tabStudent Attendance`
		WHERE student = %(student)s AND attendance_date BETWEEN %(from_date)s AND %(to_date)s
		GROUP BY DATE_FORMAT(attendance_date, '%%Y-%%m')
		ORDER BY month ASC
		""",
		{"student": student, "from_date": from_date, "to_date": to_date},
		as_dict=True,
	)

	for row in rows:
		row.percentage = _pct(cint(row.attended), cint(row.marked))
	return rows


def _get_performance(student, from_date, to_date):
	"""Per-category breakdown: how many of each grade, and the test averages."""
	rows = frappe.db.sql(
		"""
		SELECT
			category, result, COUNT(name) AS entries,
			SUM(IFNULL(marks_obtained, 0)) AS marks_obtained,
			SUM(IFNULL(total_marks, 0)) AS total_marks
		FROM `tabStudent Performance Tracker`
		WHERE student = %(student)s AND date BETWEEN %(from_date)s AND %(to_date)s
		GROUP BY category, result
		""",
		{"student": student, "from_date": from_date, "to_date": to_date},
		as_dict=True,
	)

	categories = {}
	for name in CATEGORIES:
		cfg = category_config(name)
		categories[name] = {
			"name": name,
			"entries": 0,
			"concerns": 0,
			"uses_marks": cfg["uses_marks"],
			"uses_reasons": cfg["uses_reasons"],
			"results": [{"result": r, "count": 0, "is_concern": r in LOW_RESULTS} for r in CATEGORY_RESULTS[name]],
			"marks_obtained": 0.0,
			"total_marks": 0.0,
			"percentage": None,
		}

	for row in rows:
		bucket = categories.get(row.category)
		if not bucket:
			# Left behind by the older schema — ignore rather than crash.
			continue

		count = cint(row.entries)
		bucket["entries"] += count
		if row.result in LOW_RESULTS:
			bucket["concerns"] += count
		for slot in bucket["results"]:
			if slot["result"] == row.result:
				slot["count"] += count
		bucket["marks_obtained"] += flt(row.marks_obtained)
		bucket["total_marks"] += flt(row.total_marks)

	for bucket in categories.values():
		if bucket["uses_marks"] and bucket["total_marks"]:
			bucket["percentage"] = _pct(bucket["marks_obtained"], bucket["total_marks"])
		# Share of entries that went well, for the single bar each card shows.
		bucket["good_percentage"] = _pct(bucket["entries"] - bucket["concerns"], bucket["entries"])

	# Only categories with something recorded are worth a card.
	return {
		"categories": [categories[name] for name in CATEGORIES],
		"recorded_categories": [name for name in CATEGORIES if categories[name]["entries"]],
		"total_entries": sum(c["entries"] for c in categories.values()),
		"total_concerns": sum(c["concerns"] for c in categories.values()),
	}


def _get_behaviour_incidents(student, from_date, to_date):
	"""Every Discipline/Critical day with what the student actually did.

	`by_result` splits the reasons per grade, so a parent sees which mistakes
	were only a discipline matter and which were serious enough to be Critical.
	"""
	rows = frappe.db.sql(
		"""
		SELECT p.name, p.date, p.result, p.remarks
		FROM `tabStudent Performance Tracker` p
		WHERE p.student = %(student)s
			AND p.category = 'Behaviour'
			AND p.result IN %(results)s
			AND p.date BETWEEN %(from_date)s AND %(to_date)s
		ORDER BY p.date DESC
		""",
		{
			"student": student,
			"results": tuple(REASON_REQUIRED_RESULTS),
			"from_date": from_date,
			"to_date": to_date,
		},
		as_dict=True,
	)

	if not rows:
		return _empty_behaviour()

	reason_rows = frappe.db.sql(
		"""
		SELECT parent, behaviour_reason
		FROM `tabStudent Behaviour Reason Item`
		WHERE parenttype = 'Student Performance Tracker' AND parent IN %(parents)s
		ORDER BY idx ASC
		""",
		{"parents": tuple(r.name for r in rows)},
		as_dict=True,
	)

	by_parent = {}
	for row in reason_rows:
		by_parent.setdefault(row.parent, []).append(row.behaviour_reason)

	tally = {}
	per_result = {r: {"days": 0, "tally": {}, "last_date": None} for r in REASON_REQUIRED_RESULTS}
	for row in rows:
		bucket = per_result.setdefault(row.result, {"days": 0, "tally": {}, "last_date": None})
		bucket["days"] += 1
		bucket["last_date"] = bucket["last_date"] or row.date
		for reason in by_parent.get(row.name, []):
			tally[reason] = tally.get(reason, 0) + 1
			bucket["tally"][reason] = bucket["tally"].get(reason, 0) + 1

	incidents = [
		{
			"date": row.date,
			"result": row.result,
			"remarks": row.remarks or "",
			"reasons": by_parent.get(row.name, []),
		}
		for row in rows
	]

	return {
		"incidents": incidents,
		"reason_counts": _sorted_tally(tally),
		"by_result": [
			{
				"result": result,
				"days": bucket["days"],
				"last_date": bucket["last_date"],
				"reasons": _sorted_tally(bucket["tally"]),
			}
			for result, bucket in per_result.items()
		],
	}


def _sorted_tally(tally):
	return [
		{"reason": reason, "count": count}
		for reason, count in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))
	]


def _get_test_breakdown(student, from_date, to_date):
	"""Subject-wise test record: how many tests were sat and failed in each
	subject, plus every failed paper with what it covered.

	A test can cover several subjects; it counts towards each of them. Skipped
	papers are left out — the student did not sit them.
	"""
	rows = frappe.db.sql(
		"""
		SELECT p.name, p.date, p.result, p.subject, p.marks_obtained, p.total_marks,
			p.pass_marks, p.remarks
		FROM `tabStudent Performance Tracker` p
		WHERE p.student = %(student)s
			AND p.category = 'Test'
			AND IFNULL(p.result, '') NOT IN ('', %(skip)s)
			AND p.date BETWEEN %(from_date)s AND %(to_date)s
		ORDER BY p.date DESC
		""",
		{"student": student, "skip": SKIP_RESULT, "from_date": from_date, "to_date": to_date},
		as_dict=True,
	)

	if not rows:
		return _empty_tests()

	syllabus = syllabus_of("Student Performance Tracker", [row.name for row in rows])
	titles = lesson_titles(
		[name for blocks in syllabus.values() for name in syllabus_lessons(blocks)]
	)

	subjects = {}
	failures = []
	for row in rows:
		blocks = syllabus.get(row.name, [])
		names = [b["subject"] for b in blocks if b["subject"]] or [row.subject or "No Subject"]
		failed = row.result == "Fail"

		for subject in names:
			bucket = subjects.setdefault(
				subject,
				{"subject": subject, "sat": 0, "failed": 0, "marks_obtained": 0.0, "total_marks": 0.0},
			)
			bucket["sat"] += 1
			bucket["failed"] += 1 if failed else 0
			# Marks of a multi-subject paper cannot be split, so they only feed
			# the average of a single-subject paper.
			if len(names) == 1 and row.total_marks:
				bucket["marks_obtained"] += flt(row.marks_obtained)
				bucket["total_marks"] += flt(row.total_marks)

		if failed:
			failures.append(
				{
					"date": row.date,
					"subjects": names,
					"covered": syllabus_text(blocks, titles),
					"marks_obtained": flt(row.marks_obtained) if row.total_marks else None,
					"total_marks": flt(row.total_marks) or None,
					"pass_marks": flt(row.pass_marks) or None,
					"remarks": row.remarks or "",
				}
			)

	by_subject = []
	for bucket in subjects.values():
		bucket["passed"] = bucket["sat"] - bucket["failed"]
		bucket["fail_rate"] = _pct(bucket["failed"], bucket["sat"])
		bucket["percentage"] = (
			_pct(bucket["marks_obtained"], bucket["total_marks"]) if bucket["total_marks"] else None
		)
		by_subject.append(bucket)
	# Weakest subject first — that is the conversation to have.
	by_subject.sort(key=lambda b: (-b["failed"], -b["fail_rate"], b["subject"]))

	return {
		"failures": failures,
		"by_subject": by_subject,
		"total_failed": len(failures),
		"total_sat": len(rows),
	}


def _get_timeline(student, from_date, to_date, can_attendance=True, can_performance=True, limit=40):
	"""Recent notable days, newest first — the "what happened lately" list.

	Only things worth mentioning to a parent: every performance entry, plus
	attendance days that were not a plain Present.
	"""
	performance = [] if not can_performance else frappe.db.sql(
		"""
		SELECT p.name, p.date, p.category, p.result, p.marks_obtained, p.total_marks
		FROM `tabStudent Performance Tracker` p
		WHERE p.student = %(student)s AND p.date BETWEEN %(from_date)s AND %(to_date)s
		ORDER BY p.date DESC
		LIMIT %(limit)s
		""",
		{"student": student, "from_date": from_date, "to_date": to_date, "limit": limit},
		as_dict=True,
	)

	attendance = [] if not can_attendance else frappe.db.sql(
		"""
		SELECT attendance_date, status, remarks
		FROM `tabStudent Attendance`
		WHERE student = %(student)s
			AND attendance_date BETWEEN %(from_date)s AND %(to_date)s
			AND status != 'Present'
		ORDER BY attendance_date DESC
		LIMIT %(limit)s
		""",
		{"student": student, "from_date": from_date, "to_date": to_date, "limit": limit},
		as_dict=True,
	)

	# A class can cover several subjects; the line names each with its lessons.
	syllabus = syllabus_of("Student Performance Tracker", [row.name for row in performance])
	titles = lesson_titles(
		[name for blocks in syllabus.values() for name in syllabus_lessons(blocks)]
	)

	events = []
	for row in performance:
		detail = syllabus_text(
			[dict(b, portions=[]) for b in syllabus.get(row.name, [])], titles
		)
		if row.total_marks:
			detail = " · ".join(filter(None, [detail, f"{flt(row.marks_obtained):g}/{flt(row.total_marks):g}"]))
		events.append(
			{
				"date": row.date,
				"kind": "performance",
				"title": row.category,
				"value": row.result,
				"detail": detail,
				"is_concern": row.result in LOW_RESULTS,
			}
		)

	for row in attendance:
		events.append(
			{
				"date": row.attendance_date,
				"kind": "attendance",
				"title": "Attendance",
				"value": row.status,
				"detail": row.remarks or "",
				"is_concern": row.status == "Absent",
			}
		)

	events.sort(key=lambda e: e["date"], reverse=True)
	return events[:limit]


def _build_highlights(details, attendance, performance, behaviour, tests):
	"""Three-to-five plain sentences summarising the range.

	This is the part a parent actually reads, so it is written as statements
	about their child rather than as metric names, and it always leads with
	something true and positive when there is one.
	"""
	highlights = []
	name = (details.student_name or "").split(" ")[0] or "This student"

	if attendance["school_days"]:
		highlights.append(
			{
				"tone": "good" if attendance["percentage"] >= 85 else "warn" if attendance["percentage"] >= 75 else "bad",
				"icon": "fa-calendar-check-o",
				"text": f"Attended {attendance['attended']} of {attendance['school_days']} school days "
				f"({attendance['percentage']}%) — {attendance['band']['label'].lower()}.",
			}
		)
		if attendance["best_streak"] >= 5:
			highlights.append(
				{
					"tone": "good",
					"icon": "fa-fire",
					"text": f"Best run without an absence: {attendance['best_streak']} days in a row.",
				}
			)
		if attendance["late"] >= 3:
			highlights.append(
				{
					"tone": "warn",
					"icon": "fa-clock-o",
					"text": f"Arrived late {attendance['late']} times — worth a word about mornings.",
				}
			)
	else:
		highlights.append(
			{
				"tone": "info",
				"icon": "fa-info-circle",
				"text": "No attendance was recorded for this period.",
			}
		)

	for bucket in performance["categories"]:
		if not bucket["entries"]:
			continue
		if bucket["uses_marks"] and bucket["percentage"] is not None:
			tone = "good" if bucket["percentage"] >= 75 else "warn" if bucket["percentage"] >= 40 else "bad"
			highlights.append(
				{
					"tone": tone,
					"icon": "fa-pencil-square-o",
					"text": f"{bucket['name']}: scored {bucket['percentage']}% overall across "
					f"{bucket['entries']} test(s).",
				}
			)
		elif bucket["name"] != "Behaviour":
			tone = "good" if bucket["good_percentage"] >= 80 else "warn" if bucket["good_percentage"] >= 50 else "bad"
			highlights.append(
				{
					"tone": tone,
					"icon": "fa-book",
					"text": f"{bucket['name']}: {bucket['entries'] - bucket['concerns']} of "
					f"{bucket['entries']} days went well.",
				}
			)

	weak = [b for b in tests["by_subject"] if b["failed"]]
	if weak:
		highlights.append(
			{
				"tone": "bad",
				"icon": "fa-times-circle",
				"text": "Failed tests in "
				+ ", ".join(f"{b['subject']} ({b['failed']} of {b['sat']})" for b in weak[:3])
				+ ".",
			}
		)

	incidents = behaviour["incidents"]
	if incidents:
		top = ", ".join(r["reason"] for r in behaviour["reason_counts"][:3])
		highlights.append(
			{
				"tone": "bad" if any(i["result"] == "Critical" for i in incidents) else "warn",
				"icon": "fa-exclamation-triangle",
				"text": f"{len(incidents)} behaviour concern(s) recorded" + (f" — mostly {top}." if top else "."),
			}
		)
	elif any(c["name"] == "Behaviour" and c["entries"] for c in performance["categories"]):
		highlights.append(
			{"tone": "good", "icon": "fa-smile-o", "text": f"{name} had no behaviour concerns this period."}
		)

	return highlights
