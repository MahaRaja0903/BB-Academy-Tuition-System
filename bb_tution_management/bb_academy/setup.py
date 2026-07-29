# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def setup_bb_academy():
	"""Setup roles and initial dummy records for BB Academy Module."""
	create_roles()
	seed_sms_settings()
	seed_academic_years()
	seed_schools()
	seed_standards()
	seed_batches()
	seed_fee_structures()


def seed_sms_settings():
	doc = frappe.get_single("BB SMS Settings")
	doc.enabled = 1
	doc.enable_birthday_sms = 1
	doc.enable_fee_reminder_sms = 1
	doc.enable_payment_sms = 1
	doc.save(ignore_permissions=True)


def seed_schools():
	schools = [
		{"school_name": "St. Xavier's High School", "board": "CBSE"},
		{"school_name": "Delhi Public School", "board": "CBSE"},
		{"school_name": "Kendriya Vidyalaya", "board": "CBSE"},
		{"school_name": "National Public School", "board": "ICSE"},
		{"school_name": "DAV Model School", "board": "State Board"},
	]
	for data in schools:
		if not frappe.db.exists("School", data["school_name"]):
			doc = frappe.get_doc({"doctype": "School", **data})
			doc.insert(ignore_permissions=True)
	frappe.db.commit()


def seed_academic_years():
	academic_years = [
		{
			"academic_year_name": "2025-2026",
			"start_date": "2025-04-01",
			"start_month": "April",
			"end_date": "2026-03-31",
			"end_month": "March",
			"is_active": 1
		},
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
	roles = ["Receptionist", "Teacher", "Accountant"]
	for r in roles:
		if not frappe.db.exists("Role", r):
			role_doc = frappe.get_doc({
				"doctype": "Role",
				"role_name": r,
				"desk_access": 1
			})
			role_doc.insert(ignore_permissions=True)
			frappe.db.commit()


def seed_standards():
	standards_data = [
		{"standard_name": "6", "group": "General", "academic_order": 6, "starting_payment": 5000},
		{"standard_name": "7", "group": "General", "academic_order": 7, "starting_payment": 5000},
		{"standard_name": "8", "group": "General", "academic_order": 8, "starting_payment": 5000},
		{"standard_name": "9", "group": "General", "academic_order": 9, "starting_payment": 5000},
		{"standard_name": "10 Commerce", "group": "Commerce", "academic_order": 10, "starting_payment": 10000},
		{"standard_name": "11 Commerce", "group": "Commerce", "academic_order": 11, "starting_payment": 10000},
		{"standard_name": "11 Science", "group": "Science", "academic_order": 11, "starting_payment": 10000},
		{"standard_name": "12 Commerce", "group": "Commerce", "academic_order": 12, "starting_payment": 10000},
		{"standard_name": "12 Science", "group": "Science", "academic_order": 12, "starting_payment": 10000},
	]

	for data in standards_data:
		if not frappe.db.exists("Standard", data["standard_name"]):
			doc = frappe.get_doc({
				"doctype": "Standard",
				"standard_name": data["standard_name"],
				"group": data["group"],
				"academic_order": data["academic_order"],
				"starting_payment": data["starting_payment"],
				"is_active": 1
			})
			doc.insert(ignore_permissions=True)
	frappe.db.commit()


def seed_batches():
	batches_data = [
		{"batch_name": "Batch 1", "batch_code": 1, "display_order": 1, "description": "Top Performers"},
		{"batch_name": "Batch 2", "batch_code": 2, "display_order": 2, "description": "Above Average"},
		{"batch_name": "Batch 3", "batch_code": 3, "display_order": 3, "description": "Average"},
		{"batch_name": "Batch 4", "batch_code": 4, "display_order": 4, "description": "Extra Coaching"},
	]

	for data in batches_data:
		if not frappe.db.exists("Batch", data["batch_name"]):
			doc = frappe.get_doc({
				"doctype": "Batch",
				"batch_name": data["batch_name"],
				"batch_code": data["batch_code"],
				"display_order": data["display_order"],
				"description": data["description"],
				"is_active": 1
			})
			doc.insert(ignore_permissions=True)
	frappe.db.commit()


def seed_fee_structures():
	fee_map_junior = {"Batch 1": 3000, "Batch 2": 2500, "Batch 3": 2000, "Batch 4": 1800}
	fee_map_senior = {"Batch 1": 6000, "Batch 2": 5000, "Batch 3": 4500, "Batch 4": 4000}

	junior_standards = ["6", "7", "8", "9"]
	senior_standards = ["10 Commerce", "11 Commerce", "11 Science", "12 Commerce", "12 Science"]
	batches = ["Batch 1", "Batch 2", "Batch 3", "Batch 4"]

	for std in junior_standards:
		for b in batches:
			name = f"{std} - {b}"
			if not frappe.db.exists("Fee Structure", name):
				doc = frappe.get_doc({
					"doctype": "Fee Structure",
					"standard": std,
					"batch": b,
					"monthly_fee": fee_map_junior[b],
					"effective_from": "2026-01-01",
					"is_active": 1
				})
				doc.insert(ignore_permissions=True)

	for std in senior_standards:
		for b in batches:
			name = f"{std} - {b}"
			if not frappe.db.exists("Fee Structure", name):
				doc = frappe.get_doc({
					"doctype": "Fee Structure",
					"standard": std,
					"batch": b,
					"monthly_fee": fee_map_senior[b],
					"effective_from": "2026-01-01",
					"is_active": 1
				})
				doc.insert(ignore_permissions=True)

	frappe.db.commit()
