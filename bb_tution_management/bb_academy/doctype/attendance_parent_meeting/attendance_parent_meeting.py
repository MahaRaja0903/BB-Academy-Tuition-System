# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""The parent meeting Attendance Calls asks for once a student reaches
MEETING_THRESHOLD Absent / Late days in a month. One per student per month."""

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class AttendanceParentMeeting(Document):
	def autoname(self):
		from bb_tution_management.bb_academy.attendance_calls import meeting_name

		self.name = meeting_name(self.student, self.month_start)

	def validate(self):
		student = frappe.db.get_value(
			"Student", self.student, ["student_name", "standard", "current_batch"], as_dict=True
		)
		if student:
			self.student_name = student.student_name
			self.standard = student.standard
			self.batch = student.current_batch
		if self.parents_informed and not self.parents_informed_on:
			self.parents_informed_on = now_datetime()
		if self.meeting_done and not self.meeting_on:
			self.meeting_on = now_datetime()
