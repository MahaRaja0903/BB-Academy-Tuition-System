# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class StudentAttendance(Document):
	def before_insert(self):
		"""Clear the early-out fields Frappe stamps onto every new row.

		`Document.insert()` runs `_set_defaults()`, which builds a blank doc via
		`frappe.new_doc()`. `frappe.model.create_new.set_dynamic_default_values`
		assigns `nowtime()` to *every* Time field there, unconditionally -- the
		branch sits outside the `if df.get("default")` guard -- and
		`update_if_missing()` then copies it onto this doc. A plain Present or
		Absent row therefore landed with early_out_time set to the moment it was
		saved, which made the Early Out screen report every marked student as
		already granted.

		`before_insert` runs after `_set_defaults()`, so clearing here is the
		last word. Only a row that genuinely is an early out keeps the values,
		and that path goes through late_permission.grant_early_out, which saves
		an existing row rather than inserting one.
		"""
		if self.status != "Early Outs":
			self.early_out_time = None
			self.early_out_reason = None
