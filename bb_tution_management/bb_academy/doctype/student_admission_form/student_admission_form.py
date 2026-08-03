# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class StudentAdmissionForm(Document):
	def validate(self):
		self.fetch_fees()
		self.validate_admission_number()

	def fetch_fees(self):
		if self.standard:
			starting_payment = frappe.db.get_value("Standard", self.standard, "starting_payment")
			if starting_payment is not None:
				self.starting_payment = starting_payment

		if self.standard and self.assigned_batch:
			monthly_fee = frappe.db.get_value(
				"Fee Structure",
				{
					"standard": self.standard,
					"batch": self.assigned_batch
				},
				"monthly_fee"
			)
			if monthly_fee is not None:
				self.monthly_fee = monthly_fee

	def validate_admission_number(self):
		if self.admission_number:
			existing_student = frappe.db.exists("Student", {"admission_number": self.admission_number})
			if existing_student:
				frappe.throw(_("A Student already exists with Admission Number '{0}'.").format(self.admission_number))

	def on_submit(self):
		self.db_set("status", "Approved")
		self.create_student_record()
		self.update_enquiry_status()

	def create_student_record(self):
		existing_student = frappe.db.exists("Student", {"admission_number": self.admission_number})
		if not existing_student:
			student = frappe.get_doc({
				"doctype": "Student",
				"admission_number": self.admission_number,
				"student_name": self.student_name,
				"image": self.image,
				"admission_date": self.application_date or frappe.utils.today(),
				"academic_year": self.academic_year,
				"standard": self.standard,
				"current_batch": self.assigned_batch,
				"date_of_birth": self.date_of_birth,
				"gender": self.gender,
				"father_name": self.father_name,
				"mother_name": self.mother_name,
				"parent_mobile": self.parent_mobile,
				"whatsapp_number": self.whatsapp_number or self.parent_mobile,
				"school_name": self.school_name,
				"address": self.address,
				"status": "Active"
			})
			student.insert(ignore_permissions=True)
			
			frappe.msgprint(frappe._("Student record {0} and Starting Fee Invoice created.").format(student.name))
			return

	def original_create_student_record(self):
		existing_student = frappe.db.exists("Student", {"admission_number": self.admission_number})
		if not existing_student:
			student = frappe.get_doc({
				"doctype": "Student",
				"admission_number": self.admission_number,
				"student_name": self.student_name,
				"image": self.image,
				"admission_date": self.application_date or frappe.utils.today(),
				"academic_year": self.academic_year,
				"standard": self.standard,
				"current_batch": self.assigned_batch,
				"date_of_birth": self.date_of_birth,
				"gender": self.gender,
				"father_name": self.father_name,
				"mother_name": self.mother_name,
				"parent_mobile": self.parent_mobile,
				"whatsapp_number": self.whatsapp_number or self.parent_mobile,
				"school_name": self.school_name,
				"address": self.address,
				"status": "Active"
			})
			student.insert(ignore_permissions=True)
			frappe.msgprint(
				_("Student record {0} created successfully for {1}.").format(
					student.name, self.student_name
				)
			)

	def update_enquiry_status(self):
		if self.student_enquiry:
			enquiry = frappe.get_doc("Student Enquiry Form", self.student_enquiry)
			enquiry.db_set("status", "Converted")
