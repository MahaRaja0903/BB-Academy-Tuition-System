"""Single source of truth for the Student Performance categories.

The Performance Manager PWA, the doctype controllers, the whitelisted API and
the monthly report all grade against the same categories. Keeping the option
lists here (rather than only in each doctype's Select `options`) means the
raw-SQL and bulk paths validate against exactly what the UI offers.

Test is the only test category. A batch can sit several Tests on one day, one
per Subject + Lesson + Portion combination; `combination_key` is what tells them
apart, and the same combination cannot be set twice for a batch on one day.

The PWA mirrors CATEGORIES in PerformanceManager.vue — keep the two in step.
"""

import hashlib
import re

import frappe
from frappe.utils import flt

# The grade a row carries when the teacher excused the student from the test or
# study. It is not a pass and not a fail — it is "did not sit it", and it always
# comes with a remark saying why.
SKIP_RESULT = "Skipped"

# Behaviour is never skipped — the student was in the room either way.
SKIPPABLE_CATEGORIES = ["Study", "Class", "Test", "H.W"]

# The category whose sessions are keyed by their Subject + Lesson + Portion
# combination, so one batch can hold several of them on the same day.
MULTI_SESSION_CATEGORIES = ["Test"]

# Retired categories — their rows were converted to Test by the
# performance_single_test patch.
RETIRED_TEST_CATEGORIES = ["Maths Test", "Accounts Test"]

# category -> the grades it offers, in the order the UI renders them.
CATEGORY_RESULTS = {
	"Study": ["Excellent", "Completed", "Incomplete", SKIP_RESULT],
	# Class is not graded — every student listed was present and sat the class.
	# "Attended" only records that it happened and what it covered.
	"Class": ["Attended", SKIP_RESULT],
	"Test": ["Full Mark", "Pass Mark", "Fail", SKIP_RESULT],
	# Home work set on the covered subject / lesson / portion — done or not.
	"H.W": ["Done", "Not Done", SKIP_RESULT],
	"Behaviour": ["Good", "Discipline", "Critical"],
}

CATEGORIES = list(CATEGORY_RESULTS.keys())

# Every grade any category can carry. Mirrors the `result` Select options on
# Student Performance Tracker.
ALL_RESULTS = []
for _cat in CATEGORIES:
	for _r in CATEGORY_RESULTS[_cat]:
		if _r not in ALL_RESULTS:
			ALL_RESULTS.append(_r)

# -----------------------------------------------------------------------------
# Configuration Variables
# -----------------------------------------------------------------------------

# Results that demand a specific behaviour reason to be picked from the master
REASON_REQUIRED_RESULTS = ["Discipline", "Critical"]

# Results that qualify as a "mistake" / "poor performance" metric
# Skipped is deliberately absent: an excused student has not done badly.
LOW_RESULTS = ["Incomplete", "Fail", "Not Done", "Discipline", "Critical"]

# Only students the attendance register marks with one of these statuses are
# listed for grading — you cannot rate a lesson a student did not sit through.
# A late arrival still sat the lesson, so they are graded too.
PRESENT_STATUSES = ["Present", "Late"]

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
	"Class": {
		# Subject / Lesson / Portion, same as Study — but no grade to give.
		"uses_syllabus": True,
		"uses_questions": False,
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
	"H.W": {
		# Subject / Lesson / Portion of the home work, set once for the batch.
		"uses_syllabus": True,
		"uses_questions": False,
		"uses_marks": False,
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


def categories_for_standard(standard=None):
	"""The categories the Performance Manager offers. Every standard sits the
	same ones now that the subject tests are folded into Test."""
	return list(CATEGORIES)


def is_multi_session(category):
	return category in MULTI_SESSION_CATEGORIES


def combination_key(blocks):
	"""A short, stable id for a Subject + Lesson + Portion combination.

	Order does not matter — Lesson 1 + Lesson 2 is the same test as Lesson 2 +
	Lesson 1 — so the picks are sorted before hashing.
	"""
	parts = []
	for block in blocks or []:
		parts.append(
			"{}|{}|{}".format(
				block.get("subject") or "",
				",".join(sorted(block.get("lessons") or [])),
				",".join(sorted(block.get("portions") or [])),
			)
		)
	return hashlib.md5("#".join(sorted(parts)).encode()).hexdigest()[:10]


def slug(value):
	"""Make `value` safe for a document name.

	Frappe rejects "/" outright and round-trips spaces awkwardly in URLs, and
	both appear in real Standard/Batch names ("H.W", "10 A/B").
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
