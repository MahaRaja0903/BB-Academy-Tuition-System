# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

# Grouped from the free-text reasons recorded so far.
DEFAULT_REASONS = (
	"Fees Issue",
	"Health Issue",
	"Not Interested",
	"Studies Struggle",
	"Not Satisfied with Tuition",
	"Family Problem / Relocated",
	"Batch / Timing Issue",
	"Long Absent",
	"Discipline",
	"Other",
)


class DiscontinueReason(Document):
	pass


def create_default_discontinue_reasons():
	"""Seed DEFAULT_REASONS. Idempotent — safe to re-run on every migrate."""
	for name in DEFAULT_REASONS:
		if not frappe.db.exists("Discontinue Reason", name):
			frappe.get_doc({"doctype": "Discontinue Reason", "reason_name": name}).insert(
				ignore_permissions=True
			)
