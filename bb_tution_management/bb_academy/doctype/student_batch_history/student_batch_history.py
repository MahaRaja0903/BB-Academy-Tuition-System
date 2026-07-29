# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class StudentBatchHistory(Document):
	def validate(self):
		if self.previous_batch and self.new_batch and self.previous_batch == self.new_batch:
			frappe.throw(_("Previous Batch and New Batch cannot be the same."))

	def on_submit(self):
		self.update_student_current_batch()

	def after_insert(self):
		self.update_student_current_batch()

	def update_student_current_batch(self):
		if getattr(self.flags, "ignore_student_update", False):
			return

		if self.student and self.new_batch:
			student_doc = frappe.get_doc("Student", self.student)
			if student_doc.current_batch != self.new_batch:
				student_doc.flags.ignore_batch_history = True
				student_doc.current_batch = self.new_batch
				student_doc.save(ignore_permissions=True)
