# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def setup_bb_academy():
	"""Setup roles and initial dummy records for BB Academy Module."""
	create_roles()
	setup_attendance_manager_permissions()
	seed_sms_settings()
	seed_academic_years()


def seed_sms_settings():
	doc = frappe.get_single("BB SMS Settings")
	doc.enabled = 1
	doc.enable_birthday_sms = 1
	doc.enable_fee_reminder_sms = 1
	doc.enable_payment_sms = 1
	doc.save(ignore_permissions=True)



def seed_academic_years():
	academic_years = [
		{
			"academic_year_name": "2026-2027",
			"start_date": "2026-04-01",
			"start_month": "April",
			"end_date": "2027-03-31",
			"end_month": "March",
			"is_active": 1
		}
	]
	for data in academic_years:
		if not frappe.db.exists("Academic Year", data["academic_year_name"]):
			doc = frappe.get_doc({
				"doctype": "Academic Year",
				**data
			})
			doc.insert(ignore_permissions=True)
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
