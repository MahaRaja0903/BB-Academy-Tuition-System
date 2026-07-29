# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class PaymentEntry(Document):
	def validate(self):
		self.validate_amount()
		self.validate_fee_invoice()

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
		self.send_receipt_sms()

	def send_receipt_sms(self):
		from bb_tution_management.bb_academy.sms import send_payment_confirmation
		send_payment_confirmation(self)

	def on_cancel(self):
		self.update_invoice_status(is_submit=False)

	def update_invoice_status(self, is_submit=True):
		invoice = frappe.get_doc("Fee Invoice", self.fee_invoice)
		paid_amount = float(invoice.paid_amount or 0)
		payment_amount = float(self.amount or 0)

		if is_submit:
			paid_amount += payment_amount
		else:
			paid_amount = max(0.0, paid_amount - payment_amount)

		invoice.paid_amount = paid_amount
		invoice.outstanding_amount = max(0.0, float(invoice.monthly_fee or 0) - paid_amount)

		if invoice.outstanding_amount <= 0:
			invoice.status = "Paid"
		elif invoice.paid_amount > 0:
			invoice.status = "Partially Paid"
		else:
			invoice.status = "Unpaid"

		invoice.save(ignore_permissions=True)
