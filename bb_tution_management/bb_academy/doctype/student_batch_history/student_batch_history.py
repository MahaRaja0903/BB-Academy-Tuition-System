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
		self.send_batch_change_sms_notification()

	def send_batch_change_sms_notification(self):
		if self.student and self.previous_batch and self.new_batch:
			student = frappe.db.get_value("Student", self.student, ["student_name", "parent_mobile", "standard"], as_dict=True)
			if student:
				from bb_tution_management.bb_academy.sms import send_batch_change_sms
				send_batch_change_sms(
					student_name=student.student_name,
					parent_mobile=student.parent_mobile,
					previous_batch=self.previous_batch,
					new_batch=self.new_batch,
					standard=student.standard
				)

	def update_student_current_batch(self):
		if getattr(self.flags, "ignore_student_update", False):
			return

		if self.student and self.new_batch:
			student_doc = frappe.get_doc("Student", self.student)
			if student_doc.current_batch != self.new_batch:
				student_doc.flags.ignore_batch_history = True
				student_doc.current_batch = self.new_batch
				student_doc.save(ignore_permissions=True)
