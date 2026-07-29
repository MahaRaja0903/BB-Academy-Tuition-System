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
				if not self.monthly_fee:
					self.monthly_fee = student_doc.monthly_fee or 0

	def validate_immutability(self):
		if not self.is_new():
			doc_before_save = self.get_doc_before_save()
			if doc_before_save:
				if doc_before_save.standard != self.standard:
					frappe.throw(_("Standard cannot be changed once Fee Invoice is created."))
				if doc_before_save.batch != self.batch:
					frappe.throw(_("Batch cannot be changed once Fee Invoice is created."))
				if float(doc_before_save.monthly_fee or 0) != float(self.monthly_fee or 0):
					frappe.throw(_("Monthly Fee cannot be changed once Fee Invoice is created."))

	def validate_duplicate_invoice(self):
		if self.student and self.fee_month and self.fee_year:
			existing = frappe.db.exists(
				"Fee Invoice",
				{
					"student": self.student,
					"fee_month": self.fee_month,
					"fee_year": self.fee_year,
					"docstatus": ["!=", 2],
					"name": ["!=", self.name or ""]
				}
			)
			if existing:
				frappe.throw(
					_("A Fee Invoice ({0}) already exists for Student {1} for {2} {3}.").format(
						existing, self.student, self.fee_month, self.fee_year
					)
				)

	def calculate_outstanding(self):
		monthly_fee = float(self.monthly_fee or 0)
		paid_amount = float(self.paid_amount or 0)
		self.outstanding_amount = max(0.0, monthly_fee - paid_amount)

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


@frappe.whitelist()
def auto_generate_monthly_invoices(fee_month=None, fee_year=None, auto_submit=True):
	"""Generates Fee Invoices for all active students for the target month and year."""
	if not fee_month or not fee_year:
		today = frappe.utils.getdate()
		fee_month = today.strftime("%B")
		fee_year = today.year
	else:
		fee_year = int(fee_year)

	active_students = frappe.get_all(
		"Student",
		filters={"status": "Active"},
		fields=["name", "student_name", "standard", "current_batch", "monthly_fee"]
	)

	created_count = 0
	for student in active_students:
		existing = frappe.db.exists(
			"Fee Invoice",
			{
				"student": student.name,
				"fee_month": fee_month,
				"fee_year": fee_year,
				"docstatus": ["!=", 2]
			}
		)
		if not existing:
			invoice = frappe.get_doc({
				"doctype": "Fee Invoice",
				"student": student.name,
				"fee_month": fee_month,
				"fee_year": fee_year,
				"invoice_date": frappe.utils.today(),
				"due_date": frappe.utils.add_days(frappe.utils.today(), 10)
			})
			invoice.insert(ignore_permissions=True)
			if auto_submit:
				invoice.submit()
			created_count += 1

	frappe.db.commit()
	msg = _("Generated {0} Fee Invoices for {1} {2}.").format(created_count, fee_month, fee_year)
	frappe.msgprint(msg)
	return {"created_count": created_count, "fee_month": fee_month, "fee_year": fee_year}
