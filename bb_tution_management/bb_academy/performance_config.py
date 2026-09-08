"""Single source of truth for the Student Performance categories.

The Performance Manager PWA, the doctype controllers, the whitelisted API and
the monthly report all grade against the same four categories. Keeping the
option lists here (rather than only in each doctype's Select `options`) means
the raw-SQL and bulk paths validate against exactly what the UI offers.

The PWA mirrors CATEGORIES in PerformanceManager.vue — keep the two in step.
"""

import re

# category -> the three grades it offers, in the order the UI renders them.
CATEGORY_RESULTS = {
	"Study": ["Excellent", "Completed", "Incomplete"],
	"Test": ["Full Mark", "Pass Mark", "Fail"],
	"Maths Test": ["Full Mark", "Pass Mark", "Fail"],
	"Behaviour": ["Good", "Bad", "Worst"],
}

CATEGORIES = list(CATEGORY_RESULTS.keys())

# Every grade any category can carry. Mirrors the `result` Select options on
# Student Performance Tracker.
ALL_RESULTS = []
for _cat in CATEGORIES:
	for _r in CATEGORY_RESULTS[_cat]:
		if _r not in ALL_RESULTS:
			ALL_RESULTS.append(_r)

# Grades that require the teacher to say what the student actually did.
REASON_REQUIRED_RESULTS = ["Bad", "Worst"]

# Grades that count against a student in the monthly stat chips and the report.
LOW_RESULTS = ["Incomplete", "Fail", "Bad", "Worst"]

# Only students the attendance register marks with one of these statuses are
# listed for grading — you cannot rate a lesson a student did not sit through.
# Add "Late" here if late arrivals should be gradable too.
PRESENT_STATUSES = ["Present"]

_CONFIG = {
	"Study": {
		# Subject / Lesson / Portion are entered once for the whole batch.
		"uses_syllabus": True,
		"uses_questions": True,
		"uses_marks": False,
		"uses_reasons": False,
	},
	"Test": {
		"uses_syllabus": True,
		"uses_questions": False,
		"uses_marks": True,
		"uses_reasons": False,
	},
	"Maths Test": {
		"uses_syllabus": True,
		"uses_questions": False,
		"uses_marks": True,
		"uses_reasons": False,
	},
	"Behaviour": {
		"uses_syllabus": False,
		"uses_questions": False,
		"uses_marks": False,
		"uses_reasons": True,
	},
}


def category_config(category):
	"""Feature flags for one category. Unknown categories get an all-off config
	rather than a KeyError, so a stale row never breaks a report."""
	return _CONFIG.get(
		category,
		{"uses_syllabus": False, "uses_questions": False, "uses_marks": False, "uses_reasons": False},
	)


def slug(value):
	"""Make `value` safe for a document name.

	Frappe rejects "/" outright and round-trips spaces awkwardly in URLs, and
	both appear in real Standard/Batch names ("Maths Test", "10 A/B").
	"""
	return re.sub(r"[^A-Za-z0-9]+", "-", str(value or "")).strip("-")


def derive_test_result(marks_obtained, total_marks, pass_marks):
	"""Grade a test from the marks entered.

	Full Mark at (or above) the total, Pass Mark at or above the pass mark,
	Fail below it. Returns None when there is nothing to grade against — the
	teacher then picks the grade by hand.
	"""
	if marks_obtained is None or not total_marks:
		return None

	marks = float(marks_obtained)
	total = float(total_marks)
	threshold = float(pass_marks or 0)

	if marks >= total:
		return "Full Mark"
	if threshold and marks >= threshold:
		return "Pass Mark"
	if not threshold:
		# No pass mark configured: anything short of full is a plain Pass Mark
		# only if the student scored something.
		return "Pass Mark" if marks > 0 else "Fail"
	return "Fail"
