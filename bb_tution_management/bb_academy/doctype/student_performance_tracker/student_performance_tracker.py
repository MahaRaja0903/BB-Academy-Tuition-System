# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from bb_tution_management.bb_academy.syllabus import doc_syllabus, sync_subjects
from bb_tution_management.bb_academy.performance_config import (
	CATEGORIES,
	CATEGORY_RESULTS,
	REASON_REQUIRED_RESULTS,
	SKIP_RESULT,
	category_config,
	combination_key,
	default_pass_marks,
	is_multi_session,
	slug,
)


class StudentPerformanceTracker(Document):
	def autoname(self):
		# One record per student, per date, per category. Encoding that in the
		# name lets a re-tap of the same button update the existing row instead
		# of stacking duplicates, and makes a concurrent double-save fail loudly
		# with DuplicateEntryError rather than silently writing twice.
		self.name = "PERF-{student}-{date}-{category}".format(
			student=self.student,
			date=self.date,
			category=slug(self.category),
		)
		# A batch sits several Tests a day, one per Subject + Lesson + Portion
		# combination — the combination key keeps each student's rows apart.
		if is_multi_session(self.category):
			self.test_key = combination_key(doc_syllabus(self))
			self.name += f"-{self.test_key}"
			# A Test whose combination was edited later keeps its old name, so a
			# new Test on that old combination needs a name of its own. A row that
			# really is the same combination keeps colliding, as it should.
			taken = frappe.db.get_value("Student Performance Tracker", self.name, "test_key")
			if taken and taken != self.test_key:
				self.name += "-" + frappe.generate_hash(length=4)

	def validate(self):
		self.validate_category()
		self.sync_skipped()
		self.set_student_context()
		self.set_default_pass_marks()
		self.clear_unused_fields()
		self.validate_marks()
		self.validate_behaviour_reasons()
		self.validate_test_combination()

	def validate_category(self):
		if self.category not in CATEGORIES:
			frappe.throw(f"Invalid category: {self.category}")

		allowed = CATEGORY_RESULTS[self.category]
		if self.result not in allowed:
			frappe.throw(
				f"{self.result or 'No result'} is not a valid {self.category} result. "
				f"Choose one of {', '.join(allowed)}.",
				title="Invalid Result",
			)

	def sync_skipped(self):
		"""Keep the checkbox and the grade saying the same thing.

		Either one can be the thing the user changed — the PWA sends the grade,
		the desk form has the checkbox — so whichever moved wins and the other
		follows.
		"""
		cfg = category_config(self.category)

		if not cfg["uses_skip"]:
			self.skipped = 0
			return

		if self.skipped and self.result != SKIP_RESULT:
			self.result = SKIP_RESULT
		elif self.result == SKIP_RESULT:
			self.skipped = 1
		else:
			self.skipped = 0

		if self.skipped and not (self.remarks or "").strip():
			frappe.throw(
				"Remarks are required when a student skips — say why they were excused.",
				title="Remarks Required",
			)

	def set_student_context(self):
		"""Stamp the standard/batch the student sat in, so reports can group by
		batch without re-joining Student (whose batch changes over time)."""
		if self.standard and self.batch:
			return

		row = frappe.db.get_value(
			"Student",
			self.student,
			["standard", "current_batch", "attendance_batch", "attendance_batch_set"],
			as_dict=True,
		)
		if not row:
			return

		self.standard = self.standard or row.standard
		if not self.batch:
			self.batch = row.attendance_batch if row.attendance_batch_set else row.current_batch

	def set_default_pass_marks(self):
		"""Half the paper passes unless someone says otherwise."""
		if not category_config(self.category)["uses_marks"]:
			return
		if self.total_marks and not self.pass_marks:
			self.pass_marks = default_pass_marks(self.total_marks)

	def clear_unused_fields(self):
		cfg = category_config(self.category)

		if not cfg["uses_syllabus"]:
			self.subject = None
			self.subjects = []
			self.lessons = []
			self.portions = []
		else:
			sync_subjects(self)
		if not cfg["uses_questions"]:
			self.total_questions = 0
		if not cfg["uses_marks"]:
			self.total_marks = 0
			self.pass_marks = 0
			self.marks_obtained = 0
		if not cfg["uses_reasons"] or self.result not in REASON_REQUIRED_RESULTS:
			self.behaviour_reasons = []

		# A skipped student has no score to carry — leaving the old marks on the
		# row would keep feeding the monthly test percentage.
		if self.skipped:
			self.marks_obtained = 0

	def validate_marks(self):
		if not category_config(self.category)["uses_marks"]:
			return

		if flt(self.marks_obtained) < 0:
			frappe.throw("Marks Obtained cannot be negative.")
		if self.total_marks and flt(self.marks_obtained) > flt(self.total_marks):
			frappe.throw(
				f"Marks Obtained ({self.marks_obtained}) cannot exceed Total Marks ({self.total_marks}).",
				title="Invalid Marks",
			)
		if flt(self.pass_marks) > flt(self.total_marks or 0):
			frappe.throw("Pass Marks cannot be greater than Total Marks.")

	def validate_behaviour_reasons(self):
		if self.category != "Behaviour":
			return
		if self.result not in REASON_REQUIRED_RESULTS:
			return
		if not self.behaviour_reasons:
			frappe.throw(
				f"Select at least one Behaviour Reason describing what the student did "
				f"to be marked {self.result}.",
				title="Reason Required",
			)

	def validate_test_combination(self):
		"""One Test row per student per combination per day."""
		if not is_multi_session(self.category):
			self.test_key = None
			return

		blocks = doc_syllabus(self)
		if len(blocks) > 1:
			frappe.throw(
				"A Test covers one subject. Record the next subject as a separate Test.",
				title="One Subject Per Test",
			)

		self.test_key = combination_key(blocks)
		if not (self.is_new() or self.has_value_changed("test_key")):
			return

		duplicate = frappe.db.get_value(
			"Student Performance Tracker",
			{
				"student": self.student,
				"date": self.date,
				"category": self.category,
				"test_key": self.test_key,
				"name": ["!=", self.name or ""],
			},
			"name",
		)
		if duplicate:
			frappe.throw(
				f"{self.student_name or self.student} already has this Test "
				f"(same Subject, Lesson and Portion) on {self.date}: {duplicate}.",
				title="Test Already Recorded",
			)
