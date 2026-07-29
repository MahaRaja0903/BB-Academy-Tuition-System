# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class Batch(Document):
	def validate(self):
		self.validate_batch_code()

	def validate_batch_code(self):
		if self.batch_code is None:
			frappe.throw(_("Batch Code is mandatory."))
		
		existing = frappe.db.exists("Batch", {"batch_code": self.batch_code, "name": ["!=", self.name]})
		if existing:
			frappe.throw(_("Batch Code {0} must be unique.").format(self.batch_code))
