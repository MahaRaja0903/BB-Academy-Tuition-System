# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def create_demo_data():
	"""Generates realistic demo records for testing BB Academy Tuition Management."""
	frappe.db.begin()

	# Ensure setup has been executed first
	from bb_tution_management.bb_academy.setup import setup_bb_academy
	setup_bb_academy()

	print("Creating Demo Students...")
	students_data = [
		{
			"admission_number": "ADM-2026-001",
			"student_name": "Rahul Sharma",
			"admission_date": "2026-01-05",
			"date_of_birth": "2013-04-12",
			"gender": "Boys",
			"father_name": "Suresh Sharma",
			"mother_name": "Anita Sharma",
			"father_mobile_number": "9876543210",
			"school_name": "St. Xavier's High School",
			"academic_year": "2025-2026",
			"standard": "6",
			"current_batch": "Batch 1",
			"status": "Active"
		},
		{
			"admission_number": "ADM-2026-002",
			"student_name": "Ananya Verma",
			"admission_date": "2026-01-10",
			"date_of_birth": "2010-08-25",
			"gender": "Girls",
			"father_name": "Rajesh Verma",
			"mother_name": "Sunita Verma",
			"father_mobile_number": "9876543211",
			"school_name": "Delhi Public School",
			"academic_year": "2025-2026",
			"standard": "9",
			"current_batch": "Batch 2",
			"status": "Active"
		},
		{
			"admission_number": "ADM-2026-003",
			"student_name": "Vikram Patel",
			"admission_date": "2026-01-12",
			"date_of_birth": "2009-11-03",
			"gender": "Boys",
			"father_name": "Kiran Patel",
			"mother_name": "Meena Patel",
			"father_mobile_number": "9876543212",
			"school_name": "Kendriya Vidyalaya",
			"academic_year": "2025-2026",
			"standard": "10 Commerce",
			"current_batch": "Batch 1",
			"status": "Active"
		},
		{
			"admission_number": "ADM-2026-004",
			"student_name": "Priya Nair",
			"admission_date": "2026-01-15",
			"date_of_birth": "2008-02-18",
			"gender": "Girls",
			"father_name": "Ramesh Nair",
			"mother_name": "Latha Nair",
			"father_mobile_number": "9876543213",
			"school_name": "National Public School",
			"academic_year": "2025-2026",
			"standard": "11 Science",
			"current_batch": "Batch 3",
			"status": "Active"
		},
		{
			"admission_number": "ADM-2026-005",
			"student_name": "Rohan Gupta",
			"admission_date": "2026-01-20",
			"date_of_birth": "2007-07-14",
			"gender": "Boys",
			"father_name": "Amit Gupta",
			"mother_name": "Pooja Gupta",
			"father_mobile_number": "9876543214",
			"school_name": "DAV Model School",
			"academic_year": "2025-2026",
			"standard": "12 Science",
			"current_batch": "Batch 4",
			"status": "Active"
		}
	]

	created_students = {}
	for s_data in students_data:
		existing = frappe.db.exists("Student", {"admission_number": s_data["admission_number"]})
		if existing:
			student_doc = frappe.get_doc("Student", existing)
		else:
			student_doc = frappe.get_doc({"doctype": "Student", **s_data})
			student_doc.insert(ignore_permissions=True)
		created_students[s_data["admission_number"]] = student_doc

	# Create a Batch Promotion Demonstration for Priya Nair
	print("Creating Batch Promotion History...")
	priya = created_students["ADM-2026-004"]
	if priya.current_batch == "Batch 3":
		priya.current_batch = "Batch 2"
		priya.save(ignore_permissions=True)

	# Create Invoices & Payments
	print("Creating Demo Fee Invoices & Payment Entries...")

	# 1. Rahul Sharma - Jan Invoice (Paid)
	inv_rahul_jan = create_or_get_invoice(created_students["ADM-2026-001"].name, "January")
	if inv_rahul_jan.docstatus == 0:
		inv_rahul_jan.submit()
	create_payment_if_not_exists(created_students["ADM-2026-001"].name, inv_rahul_jan.name, 3000.0, "Cash", "REC-2026-001")

	# 2. Rahul Sharma - Feb Invoice (Partially Paid)
	inv_rahul_feb = create_or_get_invoice(created_students["ADM-2026-001"].name, "February")
	if inv_rahul_feb.docstatus == 0:
		inv_rahul_feb.submit()
	create_payment_if_not_exists(created_students["ADM-2026-001"].name, inv_rahul_feb.name, 1500.0, "UPI", "UPI/2026/98214")

	# 3. Ananya Verma - Jan Invoice (Unpaid)
	inv_ananya = create_or_get_invoice(created_students["ADM-2026-002"].name, "January")
	if inv_ananya.docstatus == 0:
		inv_ananya.submit()

	# 4. Vikram Patel - Jan Invoice (Paid)
	inv_vikram = create_or_get_invoice(created_students["ADM-2026-003"].name, "January")
	if inv_vikram.docstatus == 0:
		inv_vikram.submit()
	create_payment_if_not_exists(created_students["ADM-2026-003"].name, inv_vikram.name, 6000.0, "Bank", "NEFT/2026/001928")

	# 5. Priya Nair - Jan Invoice (Unpaid)
	inv_priya = create_or_get_invoice(created_students["ADM-2026-004"].name, "January")
	if inv_priya.docstatus == 0:
		inv_priya.submit()

	# 6. Rohan Gupta - Jan Invoice (Draft)
	create_or_get_invoice(created_students["ADM-2026-005"].name, "January")

	# Create Demo Enquiries
	print("Creating Demo Student Enquiries...")
	enq1 = create_enquiry({
		"applicant_name": "Kavya Reddy",
		"enquiry_date": "2026-01-22",
		"status": "Open",
		"academic_year": "2025-2026",
		"standard": "10 Commerce",
		"gender": "Girls",
		"parent_name": "Rajesh Reddy",
		"parent_mobile": "9876543220",
		"source": "Walk-in",
		"remarks": "Interested in Commerce batch starting next month."
	})

	enq2 = create_enquiry({
		"applicant_name": "Aditya Kumar",
		"enquiry_date": "2026-01-25",
		"status": "Follow-up",
		"academic_year": "2025-2026",
		"standard": "11 Science",
		"gender": "Boys",
		"parent_name": "Manoj Kumar",
		"parent_mobile": "9876543221",
		"source": "Referral",
		"next_follow_up_date": "2026-02-10",
		"remarks": "Requested demo class for Science physics stream."
	})

	enq3 = create_enquiry({
		"applicant_name": "Deepak Sharma",
		"enquiry_date": "2026-01-18",
		"status": "Converted",
		"academic_year": "2025-2026",
		"standard": "6",
		"gender": "Boys",
		"parent_name": "Vijay Sharma",
		"parent_mobile": "9876543222",
		"source": "Website"
	})

	# Create Demo Admission Forms
	print("Creating Demo Student Admission Forms...")
	adm1 = create_admission_form({
		"student_enquiry": enq3.name,
		"academic_year": "2025-2026",
		"application_date": "2026-01-20",
		"admission_number": "ADM-2026-006",
		"student_name": "Deepak Sharma",
		"gender": "Boys",
		"father_name": "Vijay Sharma",
		"father_mobile_number": "9876543222",
		"standard": "6",
		"assigned_batch": "Batch 1"
	})
	if adm1.docstatus == 0:
		adm1.submit()

	create_admission_form({
		"academic_year": "2025-2026",
		"application_date": "2026-01-26",
		"admission_number": "ADM-2026-007",
		"student_name": "Meera Menon",
		"gender": "Girls",
		"father_name": "Unni Menon",
		"father_mobile_number": "9876543223",
		"standard": "11 Commerce",
		"assigned_batch": "Batch 2"
	})

	frappe.db.commit()
	print("Demo data creation complete!")


def create_enquiry(data):
	existing = frappe.db.exists("Student Enquiry Form", {"applicant_name": data["applicant_name"], "parent_mobile": data["parent_mobile"]})
	if existing:
		return frappe.get_doc("Student Enquiry Form", existing)

	enq = frappe.get_doc({"doctype": "Student Enquiry Form", **data})
	enq.insert(ignore_permissions=True)
	return enq


def create_admission_form(data):
	existing = frappe.db.exists("Student Admission Form", {"admission_number": data["admission_number"]})
	if existing:
		return frappe.get_doc("Student Admission Form", existing)

	adm = frappe.get_doc({"doctype": "Student Admission Form", **data})
	adm.insert(ignore_permissions=True)
	return adm


def create_or_get_invoice(student_name, month):
	existing = frappe.db.exists(
		"Fee Invoice",
		{
			"student": student_name,
			"fee_month": month,
			"docstatus": ["!=", 2]
		}
	)
	if existing:
		return frappe.get_doc("Fee Invoice", existing)

	inv = frappe.get_doc({
		"doctype": "Fee Invoice",
		"student": student_name,
		"fee_month": month,
		"invoice_date": "2026-01-05" if month == "January" else "2026-02-05",
		"due_date": "2026-01-15" if month == "January" else "2026-02-15"
	})
	inv.insert(ignore_permissions=True)
	return inv


def create_payment_if_not_exists(student_name, invoice_name, amount, mode, ref_no):
	existing = frappe.db.exists(
		"Payment Entry",
		{
			"fee_invoice": invoice_name,
			"docstatus": 1
		}
	)
	if existing:
		return frappe.get_doc("Payment Entry", existing)

	pay = frappe.get_doc({
		"doctype": "Payment Entry",
		"student": student_name,
		"fee_invoice": invoice_name,
		"payment_date": frappe.utils.today(),
		"amount": amount,
		"payment_mode": mode,
		"reference_number": ref_no,
		"remarks": f"Demo payment via {mode}"
	})
	pay.insert(ignore_permissions=True)
	pay.submit()
	return pay
