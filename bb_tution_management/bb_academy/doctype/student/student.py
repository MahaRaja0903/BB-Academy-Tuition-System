# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class Student(Document):
	def validate(self):
		self.fetch_starting_payment()
		self.fetch_monthly_fee()

	def before_save(self):
		self.track_batch_change()

	def fetch_starting_payment(self):
		if self.standard:
			starting_payment = frappe.db.get_value("Standard", self.standard, "starting_payment")
			if starting_payment is not None:
				self.starting_payment = starting_payment

	def fetch_monthly_fee(self):
		if self.standard and self.current_batch:
			monthly_fee = frappe.db.get_value(
				"Fee Structure",
				{
					"standard": self.standard,
					"batch": self.current_batch,
					# "is_active": 1,
				},
				"monthly_fee"
			)
			if monthly_fee is not None:
				self.monthly_fee = monthly_fee

	def track_batch_change(self):
		if self.is_new() or getattr(self.flags, "ignore_batch_history", False):
			return

		doc_before_save = self.get_doc_before_save()
		if doc_before_save and doc_before_save.current_batch != self.current_batch:
			previous_batch = doc_before_save.current_batch
			new_batch = self.current_batch

			history_doc = frappe.get_doc({
				"doctype": "Student Batch History",
				"student": self.name,
				"previous_batch": previous_batch,
				"new_batch": new_batch,
				"effective_date": frappe.utils.today(),
				"reason": _("Batch updated for student {0} from {1} to {2}").format(
					self.student_name, previous_batch, new_batch
				),
				"approved_by": frappe.session.user or "Administrator"
			})
			history_doc.flags.ignore_student_update = True
			history_doc.insert(ignore_permissions=True)
			frappe.msgprint(
				_("Student batch change recorded in Student Batch History from {0} to {1}.").format(
					previous_batch, new_batch
				)
			)
