# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


# Frappe's `name` column holds 140 characters; reasons can run longer.
NAME_LENGTH = 140


class BehaviourReason(Document):
	def autoname(self):
		# Short reasons stay named by their text, as every existing one is.
		# A longer one gets its opening words plus a hash; the full text is
		# kept in reason_name, which is what screens and reports show.
		reason = (self.reason_name or "").strip()
		if len(reason) <= NAME_LENGTH:
			self.name = reason
		else:
			self.name = f"{reason[:NAME_LENGTH - 10].rstrip()}-{frappe.generate_hash(length=6)}"

	def before_insert(self):
		# A reason added mid-session from the PWA has no order yet; put it at
		# the end so it does not jump ahead of the list staff already know.
		if not self.display_order:
			self.display_order = (frappe.db.sql("SELECT MAX(display_order) FROM `tabBehaviour Reason`")[0][0] or 0) + 1
