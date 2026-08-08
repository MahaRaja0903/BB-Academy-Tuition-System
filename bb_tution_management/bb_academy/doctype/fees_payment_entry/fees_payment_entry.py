# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class FeesPaymentEntry(Document):
	def validate(self):
		self.calculate_totals()
		self.validate_amount()
		self.validate_fee_invoice()

	def calculate_totals(self):
		amount = float(self.amount or 0)
		discount = float(self.discount_amount or 0)
		net_amount = amount - discount
		
		tax = 0.0
		if self.include_gst:
			tax = net_amount * 0.18
			
		self.tax_amount = tax
		self.grand_total = net_amount + tax

	def validate_amount(self):
		if self.amount is None or float(self.amount) <= 0:
			frappe.throw(_("Payment Amount must be greater than zero."))

	def validate_fee_invoice(self):
		if not self.fee_invoice:
			frappe.throw(_("Fee Invoice is mandatory."))

		invoice = frappe.get_doc("Fee Invoice", self.fee_invoice)
		if invoice.docstatus != 1:
			frappe.throw(_("Fee Invoice {0} must be submitted before accepting payment.").format(self.fee_invoice))

		if invoice.student != self.student:
			frappe.throw(
				_("Selected Fee Invoice {0} belongs to student {1}, not {2}.").format(
					self.fee_invoice, invoice.student, self.student
				)
			)

		outstanding = float(invoice.outstanding_amount or 0)
		if float(self.amount) > outstanding + 0.001:
			frappe.throw(
				_("Payment Amount ({0}) cannot exceed Invoice Outstanding Amount ({1}).").format(
					self.amount, outstanding
				)
			)

	def on_submit(self):
		self.update_invoice_status(is_submit=True)
		self.update_student_payment_detail(is_submit=True)
		self.send_receipt_sms()

	def send_receipt_sms(self):
		from bb_tution_management.bb_academy.sms import send_payment_confirmation
		send_payment_confirmation(self)

	def on_cancel(self):
		self.update_invoice_status(is_submit=False)
		self.update_student_payment_detail(is_submit=False)

	def update_invoice_status(self, is_submit=True):
		invoice = frappe.get_doc("Fee Invoice", self.fee_invoice)
		paid_amount = float(invoice.paid_amount or 0)
		payment_amount = float(self.amount or 0)

		if is_submit:
			paid_amount += payment_amount
		else:
			paid_amount = max(0.0, paid_amount - payment_amount)

		invoice.paid_amount = paid_amount
		invoice.outstanding_amount = max(0.0, float(invoice.grand_total or 0) - paid_amount)

		if invoice.outstanding_amount <= 0:
			invoice.status = "Paid"
		elif invoice.paid_amount > 0:
			invoice.status = "Partially Paid"
		else:
			invoice.status = "Unpaid"

		invoice.save(ignore_permissions=True)

	def update_student_payment_detail(self, is_submit=True):
		invoice = frappe.get_doc("Fee Invoice", self.fee_invoice)
		student = frappe.get_doc("Student", self.student)

		existing_row = None
		for row in student.get("payment_details", []):
			if row.month == invoice.fee_month:
				existing_row = row
				break

		if not existing_row:
			existing_row = student.append("payment_details", {
				"month": invoice.fee_month,
				"amount_paid": 0.0
			})

		if is_submit:
			existing_row.amount_paid = float(existing_row.amount_paid or 0) + float(self.amount or 0)
		else:
			existing_row.amount_paid = max(0.0, float(existing_row.amount_paid or 0) - float(self.amount or 0))

		existing_row.date = self.payment_date
		existing_row.pending = invoice.outstanding_amount

		if existing_row.pending <= 0:
			existing_row.status = "Paid"
		elif existing_row.amount_paid > 0:
			existing_row.status = "Partial"
		else:
			existing_row.status = "Not Paid"

		# Handling Starting Payment Concessions
		if invoice.fee_month == "Starting Payment":
			starting_fee = float(student.starting_payment or 0)
			if starting_fee > 0:
				paid_percentage = (float(existing_row.amount_paid or 0) / starting_fee) * 100
				
				# Find academic months in payment_details
				academic_rows = [row for row in student.get("payment_details", []) if row.month != "Starting Payment" and row.status != "Not Joined"]
				
				if academic_rows:
					ad_date = frappe.utils.getdate(student.admission_date) if student.admission_date else frappe.utils.getdate()
					first_month_index = 0
					if ad_date.day > 10 and len(academic_rows) > 1:
						first_month_index = 1
						
					first_month_row = academic_rows[first_month_index]
					last_month_row = academic_rows[-1]
					monthly_fee = float(student.monthly_fee or 0)
					
					if paid_percentage >= 100:
						first_month_row.status = "Paid"
						first_month_row.pending = 0
						last_month_row.status = "Paid"
						last_month_row.pending = 0
					elif paid_percentage >= 50:
						first_month_row.status = "Paid"
						first_month_row.pending = 0
						
						if float(last_month_row.amount_paid or 0) == 0:
							last_month_row.status = "Not Paid"
							last_month_row.pending = monthly_fee
					else:
						if float(first_month_row.amount_paid or 0) == 0:
							first_month_row.status = "Not Paid"
							first_month_row.pending = monthly_fee
						if float(last_month_row.amount_paid or 0) == 0:
							last_month_row.status = "Not Paid"
							last_month_row.pending = monthly_fee

		student.save(ignore_permissions=True)
