# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from frappe import _


class AcademicYear(Document):
	def validate(self):
		self.validate_dates()

	def validate_dates(self):
		if self.start_date and self.end_date:
			if getdate(self.start_date) >= getdate(self.end_date):
				frappe.throw(_("End Date must be after Start Date."))
