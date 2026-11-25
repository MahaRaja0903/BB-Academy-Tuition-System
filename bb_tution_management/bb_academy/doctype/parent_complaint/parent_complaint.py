# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""A parent's complaint taken on a follow-up call.

While it is Open the call it came from cannot be closed: the Student Mistake
Record (or the Attendance Calls card) stays on the list until staff call back,
solve it, and record how on the Complaint Calls screen.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ParentComplaint(Document):
	def validate(self):
		student = frappe.db.get_value(
			"Student", self.student, ["student_name", "standard", "current_batch"], as_dict=True
		)
		if student:
			self.student_name = student.student_name
			self.standard = student.standard
			self.batch = student.current_batch

		if not (self.complaint or "").strip():
			frappe.throw(frappe._("Write down what the parent said."))
		self.received_on = self.received_on or now_datetime()
		self.status = self.status or "Open"

		if self.status == "Resolved":
			if not self.resolved_by:
				frappe.throw(frappe._("Say who made the call that solved the complaint."))
			if not (self.resolution_notes or "").strip():
				frappe.throw(frappe._("Write down how the complaint was solved."))
			self.resolved_on = self.resolved_on or now_datetime()
