# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class FeeStructure(Document):
	def autoname(self):
		# Only set if not already set by prompt, or if you want to enforce a format
		if not self.name and self.get("standard") and self.batch:
			standards = [d.standard for d in self.get("standard") if d.standard]
			standard_str = ", ".join(standards)
			self.name = f"{standard_str} - {self.batch}"

	def validate(self):
		self.validate_monthly_fee()
		self.validate_unique_combination()

	def validate_monthly_fee(self):
		if self.monthly_fee is None or self.monthly_fee <= 0:
			frappe.throw(_("Monthly Fee must be greater than zero."))

	def validate_unique_combination(self):
		standards = [d.standard for d in self.get("standard") if d.standard]
		if not standards:
			return

		# Find existing fee structures for the same batch
		overlapping = frappe.db.get_list(
			"Fee Structure",
			filters={
				"name": ["!=", self.name or ""],
				"batch": self.batch,
			},
			fields=["name"]
		)

		if not overlapping:
			return

		overlapping_names = [d.name for d in overlapping]

		# Check if any of these fee structures have overlapping standards
		overlapping_standards = frappe.db.get_list(
			"Standard Detail",
			filters={
				"parenttype": "Fee Structure",
				"parent": ["in", overlapping_names],
				"standard": ["in", standards]
			},
			fields=["parent", "standard"]
		)

		if overlapping_standards:
			overlap = overlapping_standards[0]
			frappe.throw(
				_("A Fee Structure ({0}) already exists for Standard '{1}' and Batch '{2}'.").format(
					overlap.parent, overlap.standard, self.batch
				)
			)
