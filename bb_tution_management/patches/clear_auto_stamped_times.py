# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Erase the times Frappe stamped onto rows that were never early or late.

	`frappe.model.create_new.set_dynamic_default_values` assigns `nowtime()` to
	every Time field on a new doc, unconditionally -- the branch sits outside
	the `if df.get("default")` guard -- and `Document.insert()` reaches it
	through `_set_defaults()`. So every Student Attendance row created since
	`early_out_time` was added, and every Late Permission saved without a time,
	came out carrying the clock reading of the moment it was saved.

	The Early Out screen reads `early_out_time` to decide whether a permission
	was granted, so this made every marked student look like an early out while
	Revoke -- which filters on the status -- rejected them. The controllers now
	clear these fields on insert; this removes what the old inserts left behind.
	"""
	frappe.db.sql(
		"""
		UPDATE `tabStudent Attendance`
		SET early_out_time = NULL, early_out_reason = NULL
		WHERE status != 'Early Outs'
		  AND (early_out_time IS NOT NULL OR early_out_reason IS NOT NULL)
		"""
	)

	# A recorded time comes from `<input type="time">`, which submits whole
	# minutes; only the auto-stamped ones carry seconds or microseconds. That
	# makes the leftovers identifiable without guessing at which rows a user
	# meant to leave blank.
	frappe.db.sql(
		"""
		UPDATE `tabLate Permission`
		SET `time` = NULL
		WHERE `time` IS NOT NULL
		  AND MICROSECOND(`time`) != 0
		"""
	)
