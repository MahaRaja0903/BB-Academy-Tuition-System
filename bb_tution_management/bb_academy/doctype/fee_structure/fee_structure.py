# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class FeeStructure(Document):
	def autoname(self):
		if self.standard and self.batch:
			self.name = f"{self.standard} - {self.batch}"

	def validate(self):
		self.validate_monthly_fee()
		self.validate_unique_combination()

	def validate_monthly_fee(self):
		if self.monthly_fee is None or self.monthly_fee <= 0:
			frappe.throw(_("Monthly Fee must be greater than zero."))

	def validate_unique_combination(self):
		existing = frappe.db.exists(
			"Fee Structure",
			{
				"standard": self.standard,
				"batch": self.batch,
				"is_active": 1,
				"name": ["!=", self.name or ""]
			}
		)
		if existing and self.is_active:
			frappe.throw(
				_("An active Fee Structure already exists for Standard '{0}' and Batch '{1}'.").format(
					self.standard, self.batch
				)
			)
