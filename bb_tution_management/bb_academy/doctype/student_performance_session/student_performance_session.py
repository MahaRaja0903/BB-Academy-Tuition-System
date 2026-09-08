# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from bb_tution_management.bb_academy.performance_config import (
	CATEGORIES,
	category_config,
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

		# Clear the fields the category does not use, so a category switch in the
		# desk cannot leave a stale "Total Marks" hanging off a Study session.
		if not cfg["uses_questions"]:
			self.total_questions = 0
		if not cfg["uses_marks"]:
			self.total_marks = 0
			self.pass_marks = 0
		if not cfg["uses_syllabus"]:
			self.subject = None
			self.lesson = None
			self.portion = None

		if cfg["uses_marks"]:
			if (self.total_marks or 0) < 0 or (self.pass_marks or 0) < 0:
				frappe.throw("Total Marks and Pass Marks cannot be negative.")
			if (self.pass_marks or 0) > (self.total_marks or 0):
				frappe.throw("Pass Marks cannot be greater than Total Marks.")
