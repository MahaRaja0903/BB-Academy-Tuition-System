# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class School(Document):
	def validate(self):
		self.validate_map_coordinates()

	def validate_map_coordinates(self):
		"""Range-check the manually entered map coordinates.

		Same rule as `Student.validate_map_coordinates`: both fields are optional
		and 0 means "not set", so a school without a surveyed location simply
		stays off the Student Location Map.
		"""
		for fieldname, limit in (("latitude", 90), ("longitude", 180)):
			value = flt(self.get(fieldname))
			if not value:
				continue
			if not -limit <= value <= limit:
				frappe.throw(
					_("{0} must be between {1} and {2}.").format(
						_(self.meta.get_label(fieldname)), -limit, limit
					),
					title=_("Invalid Coordinates"),
				)
