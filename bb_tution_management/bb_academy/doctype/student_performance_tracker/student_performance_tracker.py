# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from bb_tution_management.bb_academy.performance_config import (
	CATEGORIES,
	CATEGORY_RESULTS,
	REASON_REQUIRED_RESULTS,
	category_config,
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

	def validate(self):
		self.validate_category()
		self.set_student_context()
		self.clear_unused_fields()
		self.validate_marks()
		self.validate_behaviour_reasons()

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

	def clear_unused_fields(self):
		cfg = category_config(self.category)

		if not cfg["uses_syllabus"]:
			self.subject = None
			self.lesson = None
			self.portion = None
		if not cfg["uses_questions"]:
			self.total_questions = 0
		if not cfg["uses_marks"]:
			self.total_marks = 0
			self.pass_marks = 0
			self.marks_obtained = 0
		if not cfg["uses_reasons"] or self.result not in REASON_REQUIRED_RESULTS:
			self.behaviour_reasons = []

	def validate_marks(self):
		if not category_config(self.category)["uses_marks"]:
			return

		if (self.marks_obtained or 0) < 0:
			frappe.throw("Marks Obtained cannot be negative.")
		if self.total_marks and (self.marks_obtained or 0) > self.total_marks:
			frappe.throw(
				f"Marks Obtained ({self.marks_obtained}) cannot exceed Total Marks ({self.total_marks}).",
				title="Invalid Marks",
			)

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
