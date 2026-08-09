# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class StudentAdmissionForm(Document):
	def validate(self):
		if not self.academic_year:
			today = frappe.utils.today()
			if today:
				year = int(today.split('-')[0])
				month = int(today.split('-')[1])
				start_year = year if month >= 6 else year - 1
				end_year = start_year + 1
				self.academic_year = f"{start_year}-{end_year}"
		
		if not self.admission_number and self.name and not self.name.startswith("new-"):
			self.admission_number = self.name

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
		if not self.admission_number:
			self.admission_number = self.name
			self.db_set("admission_number", self.name)
			
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
				"group": self.group,
				"current_batch": self.assigned_batch,
				"date_of_birth": self.date_of_birth,
				"gender": self.gender,
				"father_name": self.father_name,
				"father_mobile_number": self.father_mobile_number,
				"mother_name": self.mother_name,
				"mother_mobile_number": self.mother_mobile_number,
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

@frappe.whitelist()
def get_standard_ordered(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		select name from `tabStandard`
		where name like %s and is_active = 1
		order by academic_order asc
	""", ("%%%s%%" % txt,))
