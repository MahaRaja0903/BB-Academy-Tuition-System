# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def setup_bb_academy():
	"""Setup roles and initial dummy records for BB Academy Module."""
	create_roles()
	setup_attendance_manager_permissions()
	seed_performance_masters()
	seed_discontinue_reasons()


def seed_discontinue_reasons():
	"""Default categories for the Student "Discontinue Reason Category" field."""
	if not frappe.db.exists("DocType", "Discontinue Reason"):
		return

	from bb_tution_management.bb_academy.doctype.discontinue_reason.discontinue_reason import (
		create_default_discontinue_reasons,
	)

	create_default_discontinue_reasons()
	frappe.db.commit()


# Doctypes the Attendance screens read but never write. The Attendance
# Manager role held perms only on Student Attendance / Late Permission /
# Attendance Holiday, so the Standard and Batch dropdowns raised
# PermissionError and the Student-linked reports refused to run for anyone
# who wasn't also a System Manager.
ATTENDANCE_MANAGER_READ_ONLY_DOCTYPES = (
	"Student",
	"Standard",
	"Batch",
	"Late Entry Reason",
	"Early Exit Reason",
	"Academic Year",
)


def setup_attendance_manager_permissions():
	"""Grant the Attendance Manager role read access to the lookup doctypes
	the attendance UI depends on. Idempotent — safe to re-run on migrate."""
	from frappe.permissions import add_permission, update_permission_property

	role = "Attendance Manager"
	if not frappe.db.exists("Role", role):
		frappe.get_doc({
			"doctype": "Role",
			"role_name": role,
			"desk_access": 1,
		}).insert(ignore_permissions=True)

	for doctype in ATTENDANCE_MANAGER_READ_ONLY_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue

		if not frappe.db.exists(
			"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}
		):
			add_permission(doctype, role, 0)

		# Reports resolve Link columns against the target doctype, so "report"
		# is required alongside "read" for the attendance reports to run.
		for ptype in ("read", "report"):
			update_permission_property(doctype, role, 0, ptype, 1, validate=False)

	frappe.db.commit()


def seed_performance_masters():
	"""Fill the Portion master with the mark weights every standard shares.

	The Performance Manager's Portion picker is useless until the master has
	rows, and 1M ... 7M are the same everywhere, so there is nothing for anyone
	to type in by hand first. Idempotent.
	"""
	if not frappe.db.exists("DocType", "Portion"):
		return

	from bb_tution_management.bb_tution_management.doctype.portion.portion import (
		create_default_portions,
	)

	create_default_portions()
	frappe.db.commit()


def create_roles():
	roles = ["Receptionist", "Teacher", "Accountant","Owners"]
	for r in roles:
		if not frappe.db.exists("Role", r):
			role_doc = frappe.get_doc({
				"doctype": "Role",
				"role_name": r,
				"desk_access": 1
			})
			role_doc.insert(ignore_permissions=True)
			frappe.db.commit()
