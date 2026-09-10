# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe

DOCTYPE = "BB SMS Settings"


def execute():
	"""Drop the SMS feature's leftover DocType record.

	The `bb_sms_settings` files are gone from the app, but removing files does
	not remove the DocType from the database -- `bench migrate` only syncs the
	doctypes it can still find on disk. Without this the settings screen stays
	reachable at /app/bb-sms-settings and keeps showing up in the BB Academy
	module list.

	`delete_doc("DocType", ...)` clears the DocType and its DocFields but not
	the stored values, which for a Single live in `tabSingles` -- those are
	removed separately below.
	"""
	if not frappe.db.exists("DocType", DOCTYPE):
		return

	frappe.delete_doc("DocType", DOCTYPE, ignore_missing=True, force=True)
	frappe.db.delete("Singles", {"doctype": DOCTYPE})
