# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReferralCouponCode(Document):
	def on_submit(self):
		"""When a coupon is submitted, auto-append it to the Student's
		coupon_code_details child table so it becomes available for
		redemption on Fee Invoices."""
		if not self.student_id:
			frappe.throw("Student ID is required to submit a coupon.")

		student = frappe.get_doc("Student", self.student_id)

		# Avoid duplicating if the coupon is already linked
		already_linked = any(
			row.referral_coupon_code == self.name
			for row in student.get("coupon_code_details", [])
		)
		if not already_linked:
			student.append("coupon_code_details", {
				"referral_coupon_code": self.name,
				"valid_till": self.valid_till,
				"amount": self.amount,
			})
			student.save(ignore_permissions=True)

	def on_cancel(self):
		"""When a coupon is cancelled, remove it from the Student's
		coupon_code_details child table (only if it has not been used)."""
		if not self.student_id:
			return

		student = frappe.get_doc("Student", self.student_id)
		rows_to_keep = []
		for row in student.get("coupon_code_details", []):
			if row.referral_coupon_code == self.name:
				if row.used:
					frappe.throw(
						f"Coupon {self.name} has already been used on a Fee Invoice. "
						"Cancel the related Fee Invoice first before cancelling this coupon."
					)
				# Skip this row (remove it)
				continue
			rows_to_keep.append(row)

		if len(rows_to_keep) != len(student.get("coupon_code_details", [])):
			student.coupon_code_details = rows_to_keep
			student.save(ignore_permissions=True)
