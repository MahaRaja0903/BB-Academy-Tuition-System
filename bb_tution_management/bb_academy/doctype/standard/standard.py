# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class Standard(Document):
	def validate(self):
		self.validate_starting_payment()

	def validate_starting_payment(self):
		if self.starting_payment is None or self.starting_payment <= 0:
			frappe.throw(_("Starting Payment must be greater than zero."))
