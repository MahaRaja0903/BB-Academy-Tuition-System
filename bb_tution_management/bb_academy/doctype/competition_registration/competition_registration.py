# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document


class CompetitionRegistration(Document):
	def validate(self):
		self.student_name = (self.student_name or "").strip()
		self.seat_no = (self.seat_no or "").strip()
		self.validate_phone_numbers()
		self.validate_seat_no()

	def validate_phone_numbers(self):
		for field, label in (("father_number", "Father No"), ("mother_number", "Mother No")):
			number = re.sub(r"[\s-]", "", self.get(field) or "")
			if number and not re.fullmatch(r"\+?\d{10,13}", number):
				frappe.throw(f"{label} {self.get(field)} is not a valid mobile number.", title="Invalid Number")
			self.set(field, number)

	def validate_seat_no(self):
		"""Two participants cannot sit in the same seat in one competition."""
		taken_by = frappe.db.get_value(
			"Competition Registration",
			{"competition": self.competition, "seat_no": self.seat_no, "name": ["!=", self.name or ""]},
			"student_name",
		)
		if taken_by:
			frappe.throw(
				f"Seat No {self.seat_no} is already given to {taken_by} in {self.competition}.",
				title="Seat Already Taken",
			)
