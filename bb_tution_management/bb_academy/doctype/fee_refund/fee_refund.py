# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice import (
	REFUNDED,
	get_payment_row,
	update_student_totals,
)

# Roles that stand for management -- only they may approve or reject a refund.
APPROVER_ROLES = ("System Manager", "Administrator")

DISCONTINUED = "Discontinued"

# Refund reason -> Discontinue Reason, for students discontinued by a refund.
DISCONTINUE_REASON_FOR_REFUND = {
	"Not Satisfied with Tuition": "Not Satisfied with Tuition",
	"Relocating": "Family Problem / Relocated",
	"Health Reason": "Health Issue",
	"Timing Issue": "Batch / Timing Issue",
	"Others": "Other",
}


def can_approve(user=None):
	return bool(set(APPROVER_ROLES) & set(frappe.get_roles(user)))


def get_refundable_row(student_doc, month):
	"""The payment row the money was taken on for this month."""
	return get_payment_row(student_doc, month, is_submit=False)


def get_refundable_amount(row):
	return max(0.0, flt(row.amount_paid) - flt(row.refunded_amount)) if row else 0.0


@frappe.whitelist()
def get_paid_amount(student, refund_for):
	"""What can still be refunded for a month, for the form to show."""
	if not (student and refund_for):
		return 0.0
	student_doc = frappe.get_doc("Student", student)
	return get_refundable_amount(get_refundable_row(student_doc, refund_for))


class FeeRefund(Document):
	def validate(self):
		student = frappe.get_doc("Student", self.student)
		row = get_refundable_row(student, self.refund_for)
		self.paid_amount = get_refundable_amount(row)

		if not row or self.paid_amount <= 0:
			frappe.throw(
				_("{0} has no payment recorded for {1}, so there is nothing to refund.").format(
					self.student_name or self.student, self.refund_for
				)
			)

		if flt(self.refund_amount) <= 0:
			frappe.throw(_("Refund Amount must be greater than zero."))

		if flt(self.refund_amount) > self.paid_amount + 0.001:
			frappe.throw(
				_("Refund Amount ({0}) cannot be more than the amount paid for {1} ({2}).").format(
					self.refund_amount, self.refund_for, self.paid_amount
				)
			)

		self.validate_approval()

	def validate_approval(self):
		previous = self.get_doc_before_save()
		old_status = previous.approval_status if previous else "Requested"

		if self.approval_status == old_status:
			return

		if not can_approve():
			frappe.throw(_("Only management can approve or reject a refund."))

		if self.approval_status == "Requested":
			self.approved_by = None
			self.approval_date = None
		else:
			self.approved_by = frappe.session.user
			self.approval_date = nowdate()

	def before_submit(self):
		if self.approval_status != "Approved":
			frappe.throw(_("A refund can only be submitted after management approves it."))
		if not self.refund_date:
			self.refund_date = nowdate()

	def on_submit(self):
		student = frappe.get_doc("Student", self.student)
		row = get_refundable_row(student, self.refund_for)

		self.db_set("previous_row_status", row.status)
		row.refunded_amount = flt(row.refunded_amount) + flt(self.refund_amount)
		if flt(row.refunded_amount) >= flt(row.amount_paid):
			row.status = REFUNDED

		if self.discontinue_student and student.status != DISCONTINUED:
			self.db_set("previous_student_status", student.status)
			student.status = DISCONTINUED
			# The Student form requires these once the status is Discontinued.
			student.discontinued__date = student.discontinued__date or self.refund_date
			student.discontinue_reason_category = student.discontinue_reason_category or (
				DISCONTINUE_REASON_FOR_REFUND.get(self.reason, "Other")
			)
			student.discontinued_reason = student.discontinued_reason or (
				self.reason_remarks or self.reason or _("Fee refund {0}").format(self.name)
			)

		update_student_totals(student)
		student.save(ignore_permissions=True)

	def on_cancel(self):
		student = frappe.get_doc("Student", self.student)
		row = self.find_refunded_row(student)

		if row:
			row.refunded_amount = max(0.0, flt(row.refunded_amount) - flt(self.refund_amount))
			if row.status == REFUNDED and flt(row.refunded_amount) < flt(row.amount_paid):
				row.status = self.previous_row_status or "Paid"

		if self.previous_student_status and student.status == DISCONTINUED:
			student.status = self.previous_student_status

		update_student_totals(student)
		student.save(ignore_permissions=True)

	def find_refunded_row(self, student):
		rows = [
			r
			for r in student.get("payment_details", [])
			if r.month == self.refund_for and flt(r.refunded_amount) > 0
		]
		return rows[-1] if rows else None
