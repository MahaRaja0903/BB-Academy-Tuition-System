# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.exceptions import ValidationError


class TestBBAcademy(FrappeTestCase):
	def setUp(self):
		from bb_tution_management.bb_academy.setup import setup_bb_academy
		setup_bb_academy()

	def test_academic_year_validation(self):
		ay = frappe.get_doc({
			"doctype": "Academic Year",
			"academic_year_name": "Test Invalid AY",
			"start_date": "2026-04-01",
			"start_month": "April",
			"end_date": "2025-03-31", # Invalid end_date before start_date
			"end_month": "March"
		})
		self.assertRaises(ValidationError, ay.insert)

	def test_standard_validation(self):
		std = frappe.get_doc({
			"doctype": "Standard",
			"standard_name": "Test Standard",
			"group": "General",
			"academic_order": 99,
			"starting_payment": 0
		})
		self.assertRaises(ValidationError, std.insert)

	def test_batch_validation(self):
		batch = frappe.get_doc({
			"doctype": "Batch",
			"batch_name": "Test Duplicate Batch Code",
			"batch_code": 1, # Already exists from seed_batches
			"display_order": 99
		})
		self.assertRaises(ValidationError, batch.insert)

	def test_fee_structure_validation(self):
		fee_str = frappe.get_doc({
			"doctype": "Fee Structure",
			"standard": "6",
			"batch": "Batch 1", # Combination 6 - Batch 1 already exists
			"monthly_fee": 3000,
			"effective_from": "2026-01-01",
			"is_active": 1
		})
		self.assertRaises((ValidationError, frappe.DuplicateEntryError), fee_str.insert)

	def test_student_and_fee_fetching(self):
		adm_no = f"ADM-TEST-{frappe.generate_hash(length=8)}"
		student = frappe.get_doc({
			"doctype": "Student",
			"admission_number": adm_no,
			"student_name": "John Doe",
			"admission_date": "2026-01-01",
			"parent_mobile": "9876543210",
			"academic_year": "2025-2026",
			"standard": "6",
			"current_batch": "Batch 1",
			"status": "Active"
		})
		student.insert(ignore_permissions=True)
		self.assertEqual(float(student.starting_payment), 5000.0)
		self.assertEqual(float(student.monthly_fee), 3000.0)

	def test_student_batch_promotion_history(self):
		adm_no = f"ADM-TEST-{frappe.generate_hash(length=8)}"
		student = frappe.get_doc({
			"doctype": "Student",
			"admission_number": adm_no,
			"student_name": "Jane Smith",
			"admission_date": "2026-01-01",
			"parent_mobile": "9876543211",
			"academic_year": "2025-2026",
			"standard": "6",
			"current_batch": "Batch 1",
			"status": "Active"
		})
		student.insert(ignore_permissions=True)

		# Change batch
		student.current_batch = "Batch 2"
		student.save(ignore_permissions=True)

		# Check history record
		history = frappe.db.get_value(
			"Student Batch History",
			{"student": student.name, "previous_batch": "Batch 1", "new_batch": "Batch 2"},
			["name", "previous_batch", "new_batch"],
			as_dict=True
		)
		self.assertIsNotNone(history)
		self.assertEqual(history.previous_batch, "Batch 1")
		self.assertEqual(history.new_batch, "Batch 2")

	def test_fee_invoice_creation_and_immutability(self):
		adm_no = f"ADM-TEST-{frappe.generate_hash(length=8)}"
		student = frappe.get_doc({
			"doctype": "Student",
			"admission_number": adm_no,
			"student_name": "Alice Johnson",
			"admission_date": "2026-01-01",
			"parent_mobile": "9876543212",
			"academic_year": "2025-2026",
			"standard": "10 Commerce",
			"current_batch": "Batch 1",
			"status": "Active"
		})
		student.insert(ignore_permissions=True)

		invoice = frappe.get_doc({
			"doctype": "Fee Invoice",
			"student": student.name,
			"fee_month": "January",
			"fee_year": 2026
		})
		invoice.insert(ignore_permissions=True)

		self.assertEqual(invoice.standard, "10 Commerce")
		self.assertEqual(invoice.batch, "Batch 1")
		self.assertEqual(float(invoice.monthly_fee), 6000.0)
		self.assertEqual(float(invoice.outstanding_amount), 6000.0)

		# Test immutability
		invoice.standard = "11 Science"
		self.assertRaises(ValidationError, invoice.save)

	def test_payment_entry_flow(self):
		adm_no = f"ADM-TEST-{frappe.generate_hash(length=8)}"
		student = frappe.get_doc({
			"doctype": "Student",
			"admission_number": adm_no,
			"student_name": "Bob Lee",
			"admission_date": "2026-01-01",
			"parent_mobile": "9876543213",
			"academic_year": "2025-2026",
			"standard": "6",
			"current_batch": "Batch 1",
			"status": "Active"
		})
		student.insert(ignore_permissions=True)

		invoice = frappe.get_doc({
			"doctype": "Fee Invoice",
			"student": student.name,
			"fee_month": "February",
			"fee_year": 2026
		})
		invoice.insert(ignore_permissions=True)
		invoice.submit()

		# Partial Payment
		pay1 = frappe.get_doc({
			"doctype": "Payment Entry",
			"student": student.name,
			"fee_invoice": invoice.name,
			"payment_date": "2026-02-05",
			"amount": 1000.0,
			"payment_mode": "Cash"
		})
		pay1.insert(ignore_permissions=True)
		pay1.submit()

		invoice.reload()
		self.assertEqual(float(invoice.paid_amount), 1000.0)
		self.assertEqual(float(invoice.outstanding_amount), 2000.0)
		self.assertEqual(invoice.status, "Partially Paid")

		# Full Payment
		pay2 = frappe.get_doc({
			"doctype": "Payment Entry",
			"student": student.name,
			"fee_invoice": invoice.name,
			"payment_date": "2026-02-10",
			"amount": 2000.0,
			"payment_mode": "UPI"
		})
		pay2.insert(ignore_permissions=True)
		pay2.submit()

		invoice.reload()
		self.assertEqual(float(invoice.paid_amount), 3000.0)
		self.assertEqual(float(invoice.outstanding_amount), 0.0)
		self.assertEqual(invoice.status, "Paid")

	def test_student_enquiry_to_admission_form_flow(self):
		enquiry = frappe.get_doc({
			"doctype": "Student Enquiry Form",
			"applicant_name": "Test Enquiry Applicant",
			"enquiry_date": "2026-01-01",
			"status": "Open",
			"academic_year": "2025-2026",
			"standard": "6",
			"parent_name": "Parent Test",
			"parent_mobile": "9998887770"
		})
		enquiry.insert(ignore_permissions=True)

		from bb_tution_management.bb_academy.doctype.student_enquiry_form.student_enquiry_form import make_admission_form
		adm_form = make_admission_form(enquiry.name)
		self.assertEqual(adm_form.student_name, "Test Enquiry Applicant")
		self.assertEqual(adm_form.standard, "6")
		self.assertEqual(adm_form.parent_mobile, "9998887770")

	def test_student_admission_form_submission(self):
		adm_no = f"ADM-TEST-{frappe.generate_hash(length=8)}"
		adm_form = frappe.get_doc({
			"doctype": "Student Admission Form",
			"application_date": "2026-01-01",
			"academic_year": "2025-2026",
			"admission_number": adm_no,
			"student_name": "Test Adm Student",
			"standard": "6",
			"assigned_batch": "Batch 1",
			"parent_mobile": "9998887771"
		})
		adm_form.insert(ignore_permissions=True)
		adm_form.submit()

		# Verify student doc created automatically
		student = frappe.db.get_value(
			"Student",
			{"admission_number": adm_no},
			["name", "student_name", "standard", "current_batch", "status"],
			as_dict=True
		)
		self.assertIsNotNone(student)
		self.assertEqual(student.student_name, "Test Adm Student")
		self.assertEqual(student.standard, "6")
		self.assertEqual(student.current_batch, "Batch 1")
		self.assertEqual(student.status, "Active")
