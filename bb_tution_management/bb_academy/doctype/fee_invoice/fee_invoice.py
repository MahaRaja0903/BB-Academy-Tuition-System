# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class FeeInvoice(Document):
	def validate(self):
		self.fetch_student_details()
		self.validate_immutability()
		self.validate_duplicate_invoice()
		self.calculate_outstanding()
		self.update_status()

	def fetch_student_details(self):
		if self.student:
			student_doc = frappe.get_doc("Student", self.student)
			if self.is_new():
				self.standard = student_doc.standard
				self.batch = student_doc.current_batch

	def validate_immutability(self):
		if not self.is_new():
			doc_before_save = self.get_doc_before_save()
			if doc_before_save:
				if doc_before_save.standard != self.standard:
					frappe.throw(_("Standard cannot be changed once Fee Invoice is created."))
				if doc_before_save.batch != self.batch:
					frappe.throw(_("Batch cannot be changed once Fee Invoice is created."))

	def validate_duplicate_invoice(self):
		if self.student and self.fee_month and not self.is_starting_fee:
			existing = frappe.db.exists(
				"Fee Invoice",
				{
					"student": self.student,
					"fee_month": self.fee_month,
					"is_starting_fee": 0,
					"docstatus": ["!=", 2],
					"name": ["!=", self.name or ""]
				}
			)
			if existing:
				frappe.throw(
					_("A Fee Invoice ({0}) already exists for Student {1} for {2}.").format(
						existing, self.student, self.fee_month
					)
				)

	def calculate_outstanding(self):
		self.grand_total = sum([float(item.amount or 0) for item in self.get("items", [])])
		paid_amount = float(self.paid_amount or 0)
		self.outstanding_amount = max(0.0, self.grand_total - paid_amount)

	def update_status(self):
		if self.docstatus == 2:
			self.status = "Cancelled"
		elif self.docstatus == 1:
			if self.outstanding_amount <= 0:
				self.status = "Paid"
			elif float(self.paid_amount or 0) > 0:
				self.status = "Partially Paid"
			else:
				self.status = "Unpaid"
		else:
			self.status = "Draft"

	def on_submit(self):
		self.update_status()
