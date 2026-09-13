"""Single source of truth for the Student Performance categories.

The Performance Manager PWA, the doctype controllers, the whitelisted API and
the monthly report all grade against the same categories. Keeping the option
lists here (rather than only in each doctype's Select `options`) means the
raw-SQL and bulk paths validate against exactly what the UI offers.

The subject test is named after what the standard actually sits: "Maths Test"
for most standards, "Accounts Test" for the Commerce standards. Both names are
valid categories everywhere; which one a standard offers is decided by
`test_category_for_standard`.

The PWA mirrors CATEGORIES in PerformanceManager.vue — keep the two in step.
"""

import re

import frappe
from frappe.utils import flt

# The grade a row carries when the teacher excused the student from the test or
# study. It is not a pass and not a fail — it is "did not sit it", and it always
# comes with a remark saying why.
SKIP_RESULT = "Skipped"

# Behaviour is never skipped — the student was in the room either way.
SKIPPABLE_CATEGORIES = ["Study", "Test", "Maths Test", "Accounts Test"]

# The subject-specific test, one per standard. "Maths Test" is the default;
# Commerce standards sit "Accounts Test" instead.
SUBJECT_TEST_CATEGORIES = ["Maths Test", "Accounts Test"]
DEFAULT_SUBJECT_TEST = "Maths Test"
COMMERCE_SUBJECT_TEST = "Accounts Test"

# category -> the grades it offers, in the order the UI renders them.
CATEGORY_RESULTS = {
	"Study": ["Excellent", "Completed", "Incomplete", SKIP_RESULT],
	"Test": ["Full Mark", "Pass Mark", "Fail", SKIP_RESULT],
	"Maths Test": ["Full Mark", "Pass Mark", "Fail", SKIP_RESULT],
	"Accounts Test": ["Full Mark", "Pass Mark", "Fail", SKIP_RESULT],
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
# Skipped is deliberately absent: an excused student has not done badly.
LOW_RESULTS = ["Incomplete", "Fail", "Bad", "Worst"]

# Only students the attendance register marks with one of these statuses are
# listed for grading — you cannot rate a lesson a student did not sit through.
# Add "Late" here if late arrivals should be gradable too.
PRESENT_STATUSES = ["Present"]

# Half the paper is a pass, unless the teacher overrides it for the day.
PASS_MARK_PERCENT = 50.0

# A student who drops a single mark has still answered the paper, so the top
# grade starts one mark below the total: 49/50 is a Full Mark.
FULL_MARK_TOLERANCE = 1.0

_CONFIG = {
	"Study": {
		# Subject / Lesson / Portion are entered once for the whole batch.
		"uses_syllabus": True,
		"uses_questions": True,
		"uses_marks": False,
		"uses_reasons": False,
		"uses_skip": True,
	},
	"Test": {
		"uses_syllabus": True,
		"uses_questions": False,
		"uses_marks": True,
		"uses_reasons": False,
		"uses_skip": True,
	},
	"Maths Test": {
		"uses_syllabus": True,
		"uses_questions": False,
		"uses_marks": True,
		"uses_reasons": False,
		"uses_skip": True,
	},
	"Accounts Test": {
		"uses_syllabus": True,
		"uses_questions": False,
		"uses_marks": True,
		"uses_reasons": False,
		"uses_skip": True,
	},
	"Behaviour": {
		"uses_syllabus": False,
		"uses_questions": False,
		"uses_marks": False,
		"uses_reasons": True,
		"uses_skip": False,
	},
}


def category_config(category):
	"""Feature flags for one category. Unknown categories get an all-off config
	rather than a KeyError, so a stale row never breaks a report."""
	return _CONFIG.get(
		category,
		{
			"uses_syllabus": False,
			"uses_questions": False,
			"uses_marks": False,
			"uses_reasons": False,
			"uses_skip": False,
		},
	)


def test_category_for_standard(standard):
	"""Which subject test this standard sits.

	Set explicitly on the Standard master; falling back to the standard's Group
	means the Commerce standards read "Accounts Test" straight after upgrading,
	without anyone having to touch the master first.
	"""
	if not standard:
		return DEFAULT_SUBJECT_TEST

	row = frappe.db.get_value("Standard", standard, ["test_category", "group"], as_dict=True)
	if not row:
		return DEFAULT_SUBJECT_TEST

	if row.get("test_category") in SUBJECT_TEST_CATEGORIES:
		return row["test_category"]
	if row.get("group") == "Commerce":
		return COMMERCE_SUBJECT_TEST
	return DEFAULT_SUBJECT_TEST


def categories_for_standard(standard):
	"""The categories the Performance Manager offers for this standard — every
	shared one, plus the single subject test the standard actually sits."""
	subject_test = test_category_for_standard(standard)
	return [c for c in CATEGORIES if c not in SUBJECT_TEST_CATEGORIES or c == subject_test]


def slug(value):
	"""Make `value` safe for a document name.

	Frappe rejects "/" outright and round-trips spaces awkwardly in URLs, and
	both appear in real Standard/Batch names ("Maths Test", "10 A/B").
	"""
	return re.sub(r"[^A-Za-z0-9]+", "-", str(value or "")).strip("-")


def default_pass_marks(total_marks):
	"""Half the total, rounded to the nearest half mark — the pass mark the
	teacher gets handed before overriding it."""
	total = flt(total_marks)
	if total <= 0:
		return 0.0
	return round(total * PASS_MARK_PERCENT / 100.0 * 2) / 2


def full_mark_threshold(total_marks, pass_marks=None):
	"""The score from which a paper counts as a Full Mark.

	One dropped mark still counts, so it is normally `total - 1`. On a paper so
	short that the allowance would reach the pass mark (or below zero), the
	threshold falls back to the total — otherwise a 2-mark test would grade a
	bare pass as full marks.
	"""
	total = flt(total_marks)
	if total <= 0:
		return 0.0

	threshold = total - FULL_MARK_TOLERANCE
	if threshold <= 0 or threshold <= flt(pass_marks or 0):
		return total
	return threshold


def derive_test_result(marks_obtained, total_marks, pass_marks):
	"""Grade a test from the marks entered.

	Full Mark from one mark below the total up, Pass Mark at or above the pass
	mark, Fail below it. Returns None when there is nothing to grade against —
	the teacher then picks the grade by hand.
	"""
	if marks_obtained is None or not total_marks:
		return None

	marks = flt(marks_obtained)
	total = flt(total_marks)
	threshold = flt(pass_marks) if pass_marks else default_pass_marks(total)

	if marks >= full_mark_threshold(total, threshold):
		return "Full Mark"
	if threshold and marks >= threshold:
		return "Pass Mark"
	if not threshold:
		# No pass mark configured: anything short of full is a plain Pass Mark
		# only if the student scored something.
		return "Pass Mark" if marks > 0 else "Fail"
	return "Fail"
