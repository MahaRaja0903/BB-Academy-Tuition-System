# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from bb_tution_management.bb_academy.performance_config import (
	CATEGORIES,
	category_config,
	default_pass_marks,
	slug,
)


class StudentPerformanceSession(Document):
	def autoname(self):
		# One setup row per batch, per date, per category — the name encodes that
		# uniqueness so a second save of the same setup updates instead of
		# creating a duplicate.
		self.name = "SPS-{date}-{standard}-{batch}-{category}".format(
			date=self.date,
			standard=slug(self.standard),
			batch=slug(self.batch),
			category=slug(self.category),
		)

	def validate(self):
		if self.category not in CATEGORIES:
			frappe.throw(f"Invalid category: {self.category}")

		cfg = category_config(self.category)

		# "Not planned for this day" is the management saying no Study/Test was
		# scheduled at all. Behaviour is always observed, so it cannot be one.
		if self.no_session and not cfg["uses_skip"]:
			frappe.throw(f"{self.category} cannot be marked as not planned.")
		if not self.no_session:
			self.no_session_reason = None

		# Clear the fields the category does not use, so a category switch in the
		# desk cannot leave a stale "Total Marks" hanging off a Study session.
		if not cfg["uses_questions"]:
			self.total_questions = 0
		if not cfg["uses_marks"]:
			self.total_marks = 0
			self.pass_marks = 0
		if not cfg["uses_syllabus"]:
			self.subject = None
			self.lessons = []
			self.portions = []

		if cfg["uses_marks"]:
			if flt(self.total_marks) < 0 or flt(self.pass_marks) < 0:
				frappe.throw("Total Marks and Pass Marks cannot be negative.")
			# Half the paper is the pass mark until the teacher overrides it.
			if self.total_marks and not self.pass_marks:
				self.pass_marks = default_pass_marks(self.total_marks)
			if flt(self.pass_marks) > flt(self.total_marks):
				frappe.throw("Pass Marks cannot be greater than Total Marks.")
