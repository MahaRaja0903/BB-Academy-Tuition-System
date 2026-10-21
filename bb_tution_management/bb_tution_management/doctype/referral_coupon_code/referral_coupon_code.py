# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

DETAIL_DOCTYPE = "Referral Coupon Code Detail"


class ReferralCouponCode(Document):
	def validate(self):
		if not self.student_id:
			frappe.throw(_("Student ID is required."))

	def after_insert(self):
		"""Add the coupon to the student's coupon_code_details table so it can
		be redeemed on Fee Invoices, whether it was created from a referral
		admission or directly from the Referral Coupon Code form."""
		self.link_to_student(self.student_id)

	def on_update(self):
		previous = self.get_doc_before_save()
		if not previous:
			return

		if previous.student_id != self.student_id:
			self.unlink_from_student(previous.student_id)
			self.link_to_student(self.student_id)
		elif previous.amount != self.amount or previous.valid_till != self.valid_till:
			for name in get_detail_rows(self.name, self.student_id):
				frappe.db.set_value(
					DETAIL_DOCTYPE, name, {"amount": self.amount, "valid_till": self.valid_till}
				)

	def on_trash(self):
		self.unlink_from_student(self.student_id)

	def link_to_student(self, student):
		if not student or get_detail_rows(self.name, student):
			return

		# Insert the child row directly so the student's own save hooks don't run
		idx = (
			frappe.db.count(
				DETAIL_DOCTYPE,
				{"parent": student, "parenttype": "Student", "parentfield": "coupon_code_details"},
			)
			+ 1
		)
		frappe.get_doc({
			"doctype": DETAIL_DOCTYPE,
			"parent": student,
			"parenttype": "Student",
			"parentfield": "coupon_code_details",
			"idx": idx,
			"referral_coupon_code": self.name,
			"valid_till": self.valid_till,
			"amount": self.amount,
		}).db_insert()

	def unlink_from_student(self, student):
		if not student:
			return

		for name in get_detail_rows(self.name, student):
			if frappe.db.get_value(DETAIL_DOCTYPE, name, "used"):
				frappe.throw(
					_("Coupon {0} has already been used on a Fee Invoice and cannot be removed from the student.").format(
						self.name
					)
				)
			frappe.db.delete(DETAIL_DOCTYPE, {"name": name})


def get_detail_rows(coupon, student):
	return frappe.get_all(
		DETAIL_DOCTYPE,
		filters={
			"referral_coupon_code": coupon,
			"parent": student,
			"parenttype": "Student",
			"parentfield": "coupon_code_details",
		},
		pluck="name",
	)
