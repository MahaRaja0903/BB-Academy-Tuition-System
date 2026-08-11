# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def setup_bb_academy():
	"""Setup roles and initial dummy records for BB Academy Module."""
	create_roles()
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
