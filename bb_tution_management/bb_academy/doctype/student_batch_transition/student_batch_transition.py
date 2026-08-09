# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class StudentBatchTransition(Document):
	def validate(self):
		if self.previous_batch and self.new_batch and self.previous_batch == self.new_batch:
			frappe.throw(_("Previous Batch and New Batch cannot be the same."))

	def before_submit(self):
		self.update_student_current_batch()
		self.send_batch_change_sms_notification()
		self.show_transition_message()

	def show_transition_message(self):
		if self.student and self.new_batch and self.status:
			student_doc = frappe.get_doc("Student", self.student)
			gender = student_doc.gender
			pronoun = "His" if gender == "Male" else ("Her" if gender == "Female" else "Their")
			
			if self.status == "Promotion":
				status_html = "<span style='color: #10b981; font-weight: bold;'>Promoted</span>"
			else:
				status_html = "<span style='color: #ef4444; font-weight: bold;'>Demoted</span>"
				
			msg = f"""
				<div style='padding: 10px;'>
					<p style='font-size: 16px;'>Student <strong>{student_doc.student_name}</strong> has been {status_html} to Batch <strong>{self.new_batch}</strong>.</p>
					<p style='font-size: 14px;'>{pronoun} New Monthly Fees will be Updated based on the current Batch.</p>
				</div>
			"""
			frappe.msgprint(msg, title="Batch Transition Successful", indicator="green")

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
