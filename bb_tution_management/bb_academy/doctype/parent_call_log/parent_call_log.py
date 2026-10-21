# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""One call home, and the exact mistakes it told the parents about.

The rows in `mistakes` are what restart the count: Pending Call Works counts
only the mistakes no call has covered yet, so a mistake made after this call
starts a fresh count however many came before it.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class ParentCallLog(Document):
	def validate(self):
		if self.called_on and get_datetime(self.called_on) > now_datetime():
			frappe.throw(frappe._("The call cannot be in the future."))

		student = frappe.db.get_value(
			"Student", self.student, ["student_name", "standard", "current_batch"], as_dict=True
		)
		if student:
			self.student_name = student.student_name
			self.standard = self.standard or student.standard
			self.batch = self.batch or student.current_batch

		categories = []
		for row in self.mistakes or []:
			if row.category not in categories:
				categories.append(row.category)
		self.categories = ", ".join(categories)
		self.mistake_count = len(self.mistakes or [])
