# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

# Seeded on migrate — the mark weights every standard shares.
DEFAULT_PORTIONS = ["1M", "2M", "3M", "4M", "5M", "7M"]


class Portion(Document):
	def validate(self):
		self.portion_name = (self.portion_name or "").strip()
		if not self.portion_name:
			frappe.throw("Portion is required.")


def portions(include=None):
	"""The Portion master, minus anything switched off.

	`include` keeps portions already saved on a record visible even after they
	are disabled, so opening that record does not silently drop them.
	"""
	# Raw SQL because the "unordered portions sort last" expression is a function
	# call, and frappe.get_all rejects those in order_by as an illegal query.
	rows = frappe.db.sql(
		"""
		SELECT name, portion_name, portion_order
		FROM `tabPortion`
		WHERE disabled = 0
		ORDER BY IF(portion_order = 0, 999999, portion_order) ASC, portion_name ASC
		""",
		as_dict=True,
	)

	known = {r.name for r in rows}
	for name in include or []:
		if name in known or not frappe.db.exists("Portion", name):
			continue
		rows.append(
			frappe.db.get_value(
				"Portion", name, ["name", "portion_name", "portion_order"], as_dict=True
			)
		)

	return rows


def create_default_portions():
	"""Seed 1M … 7M. Idempotent — safe to re-run on every migrate."""
	for index, name in enumerate(DEFAULT_PORTIONS, start=1):
		if frappe.db.exists("Portion", name):
			continue
		frappe.get_doc(
			{"doctype": "Portion", "portion_name": name, "portion_order": index}
		).insert(ignore_permissions=True)
