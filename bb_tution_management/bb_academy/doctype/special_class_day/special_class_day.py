# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SpecialClassDay(Document):
	"""Cancels a holiday for the scope it covers.

	The register declares a day a holiday up front, but a class is sometimes
	taken anyway — a revision session before an exam, a rescheduled test, a
	rain holiday that cleared. Without this the day stays permanently
	unrecordable: attendance refuses to save, and performance refuses in turn
	because it only grades students who are marked Present.
	"""

	def validate(self):
		self.validate_scope()
		self.validate_duplicate()

	def validate_scope(self):
		if self.scope in ("Standard", "Standard + Batch") and not self.standard:
			frappe.throw(f"Standard is required for the {self.scope} scope.")
		if self.scope == "Standard + Batch" and not self.batch:
			frappe.throw("Batch is required for the Standard + Batch scope.")

		# Clear the fields the scope does not use, so a narrowed-then-widened
		# record cannot keep matching on a standard nobody can see on the form.
		if self.scope == "Entire School":
			self.standard = None
			self.batch = None
		elif self.scope == "Standard":
			self.batch = None

	def validate_duplicate(self):
		existing = frappe.db.get_value(
			"Special Class Day",
			{
				"class_date": self.class_date,
				"scope": self.scope,
				"standard": self.standard or "",
				"batch": self.batch or "",
				"name": ["!=", self.name or ""],
			},
			"name",
		)
		if existing:
			frappe.throw(
				f"{existing} already records a class on {self.class_date} for this scope.",
				title="Already Recorded",
			)
