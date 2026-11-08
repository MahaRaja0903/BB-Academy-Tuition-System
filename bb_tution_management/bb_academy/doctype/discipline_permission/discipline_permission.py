# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import formatdate, getdate

from bb_tution_management.bb_academy.late_permission import (
	allowed_permission_reasons,
	excuse_behaviour_row,
)


class DisciplinePermission(Document):
	def validate(self):
		self.validate_dates()
		self.validate_reasons()

	def validate_dates(self):
		"""A permission covers Start Date to End Date, and a student holds only
		one at a time — otherwise a day would have two answers to "what is
		this student excused from?"."""
		self.to_date = self.to_date or self.from_date
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw("End Date cannot be before the Start Date.", title="Invalid Dates")

		overlap = frappe.db.get_value(
			"Discipline Permission",
			{
				"student": self.student,
				"name": ["!=", self.name or ""],
				"from_date": ["<=", self.to_date],
				"to_date": [">=", self.from_date],
			},
			["name", "from_date", "to_date"],
			as_dict=True,
		)
		if overlap:
			frappe.throw(
				f"{self.student_name or self.student} already has a Discipline Permission from "
				f"{formatdate(overlap.from_date)} to {formatdate(overlap.to_date)} ({overlap.name}). "
				"Edit that one instead.",
				title="Permission Already Exists",
			)

	def validate_reasons(self):
		"""Only the reasons BB Academy Settings allows can be permitted, once each."""
		allowed = {r.name for r in allowed_permission_reasons()}
		seen = []
		for row in self.behaviour_reasons:
			if row.behaviour_reason not in allowed:
				frappe.throw(
					f"{row.behaviour_reason} cannot be granted as a Discipline Permission. "
					"Add it under BB Academy Settings → Discipline Permission first.",
					title="Reason Not Allowed",
				)
			if row.behaviour_reason not in seen:
				seen.append(row.behaviour_reason)
		self.set("behaviour_reasons", [{"behaviour_reason": r} for r in seen])
		if not seen:
			frappe.throw("Pick at least one Behaviour Reason to permit.", title="Reason Required")

	def on_update(self):
		# Behaviour grades given before the permission came in are excused too.
		excuse_behaviour_row(self.student, self.from_date, self.to_date)
