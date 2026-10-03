# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class StudentHoliday(Document):
	"""A holiday for one student over a date range.

	Some schools give leave to only part of a batch — e.g. students who have
	finished their exams — so the batch still meets but these students do
	not. Attendance treats them as off rather than pending or absent.
	"""

	def validate(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw("To Date cannot be before From Date.")

		if not self.batch:
			stu = frappe.db.get_value(
				"Student",
				self.student,
				["attendance_batch_set", "attendance_batch", "current_batch"],
				as_dict=True,
			)
			if stu:
				self.batch = stu.attendance_batch if stu.attendance_batch_set else stu.current_batch

		self.validate_overlap()

	def validate_overlap(self):
		existing = frappe.db.get_value(
			"Student Holiday",
			{
				"student": self.student,
				"from_date": ["<=", self.to_date],
				"to_date": [">=", self.from_date],
				"name": ["!=", self.name or ""],
			},
			["name", "from_date", "to_date"],
			as_dict=True,
		)
		if existing:
			frappe.throw(
				f"{self.student_name or self.student} already has a holiday from "
				f"{existing.from_date} to {existing.to_date} ({existing.name}).",
				title="Overlapping Holiday",
			)
