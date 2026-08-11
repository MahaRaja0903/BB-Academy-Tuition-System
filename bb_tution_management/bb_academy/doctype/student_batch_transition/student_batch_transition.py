# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint

from bb_tution_management.bb_academy.doctype.fee_structure.fee_structure import get_monthly_fee


class StudentBatchTransition(Document):
	def validate(self):
		if self.previous_batch and self.new_batch and self.previous_batch == self.new_batch:
			frappe.throw(_("Previous Batch and New Batch cannot be the same."))

		self.set_status()

	def set_status(self):
		"""Derive Promotion / Demote from where the batches sit in the batch order.

		display_order ranks batches best-first, so moving to a *higher*
		display_order (1 -> 2) is a demotion.

		Done here rather than only in the form script so transitions created in
		code (e.g. from a batch change on the Student form) are classified the
		same way as ones entered by hand.
		"""
		if not (self.previous_batch and self.new_batch):
			return

		previous_order = cint(frappe.db.get_value("Batch", self.previous_batch, "display_order"))
		new_order = cint(frappe.db.get_value("Batch", self.new_batch, "display_order"))

		self.status = "Demote" if new_order > previous_order else "Promotion"

	def before_submit(self):
		monthly_fee = self.update_student_current_batch()
		self.send_batch_change_sms_notification()
		self.show_transition_message(monthly_fee)

	def show_transition_message(self, monthly_fee=None):
		if self.student and self.new_batch and self.status:
			student_doc = frappe.get_doc("Student", self.student)
			gender = student_doc.gender
			pronoun = "His" if gender == "Male" else ("Her" if gender == "Female" else "Their")

			if self.status == "Promotion":
				status_html = "<span style='color: #10b981; font-weight: bold;'>Promoted</span>"
			else:
				status_html = "<span style='color: #ef4444; font-weight: bold;'>Demoted</span>"

			if monthly_fee is None:
				fee_line = _("No Fee Structure is defined for this Standard and Batch, so {0} Monthly Fees is unchanged.").format(pronoun.lower())
			else:
				fee_line = _("{0} Monthly Fees is now {1}.").format(pronoun, frappe.format_value(monthly_fee, {"fieldtype": "Currency"}))

			msg = f"""
				<div style='padding: 10px;'>
					<p style='font-size: 16px;'>Student <strong>{student_doc.student_name}</strong> has been {status_html} to Batch <strong>{self.new_batch}</strong>.</p>
					<p style='font-size: 14px;'>{fee_line}</p>
				</div>
			"""
			frappe.msgprint(msg, title=_("Batch Transition Successful"), indicator="green")

	def send_batch_change_sms_notification(self):
		if not (self.student and self.previous_batch and self.new_batch):
			return

		from bb_tution_management.bb_academy.sms import get_student_mobiles, send_batch_change_sms

		student = frappe.db.get_value(
			"Student", self.student, ["student_name", "standard"], as_dict=True
		)
		if not student:
			return

		# A gateway problem should not stop the student being moved.
		try:
			send_batch_change_sms(
				student_name=student.student_name,
				mobiles=get_student_mobiles(self.student),
				previous_batch=self.previous_batch,
				new_batch=self.new_batch,
				standard=student.standard,
			)
		except Exception:
			self.log_error("Batch change SMS failed")
			frappe.msgprint(
				_("The batch was updated but the SMS notification could not be sent."),
				indicator="orange",
				alert=True,
			)

	def update_student_current_batch(self):
		"""Move the student into the new batch.

		Returns the student's monthly fee after the move, or None when no Fee
		Structure covers their standard in the new batch. Saving the Student
		re-prices them: Student.validate() pulls the monthly fee for the new
		standard/batch pair and drops any discount agreed for the old batch.
		"""
		if getattr(self.flags, "ignore_student_update", False):
			return None

		if not (self.student and self.new_batch):
			return None

		student_doc = frappe.get_doc("Student", self.student)
		if student_doc.current_batch != self.new_batch:
			student_doc.flags.ignore_batch_history = True
			student_doc.current_batch = self.new_batch
			student_doc.save(ignore_permissions=True)

		return get_monthly_fee(student_doc.standard, self.new_batch)
