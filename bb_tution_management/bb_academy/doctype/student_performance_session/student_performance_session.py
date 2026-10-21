# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from bb_tution_management.bb_academy.syllabus import doc_syllabus, sync_subjects, syllabus_text
from bb_tution_management.bb_academy.performance_config import (
	CATEGORIES,
	category_config,
	combination_key,
	default_pass_marks,
	is_multi_session,
	slug,
)


class StudentPerformanceSession(Document):
	def autoname(self):
		# One setup row per batch, per date, per category — the name encodes that
		# uniqueness so a second save of the same setup updates instead of
		# creating a duplicate. A Test is one per Subject + Lesson + Portion
		# combination, so its combination key is part of the name too.
		self.name = "SPS-{date}-{standard}-{batch}-{category}".format(
			date=self.date,
			standard=slug(self.standard),
			batch=slug(self.batch),
			category=slug(self.category),
		)
		if is_multi_session(self.category) and not self.no_session:
			self.test_key = combination_key(doc_syllabus(self))
			self.name += f"-{self.test_key}"
			# A Test whose combination was edited later keeps its old name, so a
			# new Test on that old combination needs a name of its own. A row that
			# really is the same combination keeps colliding, as it should.
			taken = frappe.db.get_value("Student Performance Session", self.name, "test_key")
			if taken and taken != self.test_key:
				self.name += "-" + frappe.generate_hash(length=4)

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
			self.subjects = []
			self.lessons = []
			self.portions = []
		else:
			sync_subjects(self)

		if cfg["uses_marks"]:
			if flt(self.total_marks) < 0 or flt(self.pass_marks) < 0:
				frappe.throw("Total Marks and Pass Marks cannot be negative.")
			# Half the paper is the pass mark until the teacher overrides it.
			if self.total_marks and not self.pass_marks:
				self.pass_marks = default_pass_marks(self.total_marks)
			if flt(self.pass_marks) > flt(self.total_marks):
				frappe.throw("Pass Marks cannot be greater than Total Marks.")

		self.validate_test_combination()

	def validate_test_combination(self):
		"""A Test covers one subject, and a batch cannot sit the same Subject +
		Lesson + Portion combination twice on one day — that test is already
		being graded, so the teacher should finish it rather than start it again."""
		if not is_multi_session(self.category) or self.no_session:
			self.test_key = None
			return

		blocks = doc_syllabus(self)
		subjects = [b["subject"] for b in blocks if b["subject"]]
		if not subjects:
			frappe.throw("Pick the Subject this Test is on.", title="Subject Required")
		if len(blocks) > 1:
			frappe.throw(
				"A Test covers one subject. Add a separate Test for the next subject.",
				title="One Subject Per Test",
			)

		self.test_key = combination_key(blocks)
		filters = {
			"date": self.date,
			"standard": self.standard,
			"batch": self.batch,
			"category": self.category,
			"test_key": self.test_key,
			"no_session": 0,
		}
		# A new Test on a taken combination gets the taken Test's name, so it
		# must not be excluded by name until it is actually saved.
		if not self.is_new():
			filters["name"] = ["!=", self.name]
		duplicate = frappe.db.get_value("Student Performance Session", filters, "name")
		if duplicate:
			frappe.throw(
				f"A Test on {syllabus_text(blocks) or subjects[0]} is already added for "
				f"{self.batch} on {self.date}. Complete that one, or change the Lesson or Portion.",
				title="Test Already Added",
			)
