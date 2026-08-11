# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe

from bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice import update_student_totals


def execute():
	"""Fill in total_paid_amount / total_pending_amount for students that
	existed before those fields did. They are kept up to date from then on by
	Student.validate() and by every Fee Invoice submit or cancel."""
	for name in frappe.get_all("Student", pluck="name"):
		student = frappe.get_doc("Student", name)
		update_student_totals(student)

		frappe.db.set_value(
			"Student",
			name,
			{
				"total_paid_amount": student.total_paid_amount,
				"total_pending_amount": student.total_pending_amount,
			},
			update_modified=False,
		)
