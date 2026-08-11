# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class StudentEnquiryForm(Document):
	def validate(self):
		if not self.academic_year:
			self.academic_year = get_academic_year(self.enquiry_date or frappe.utils.today())


@frappe.whitelist()
def get_academic_year(date=None):
	if not date:
		date = frappe.utils.today()
	
	ay = frappe.db.get_value(
		"Academic Year",
		{
			"start_date": ["<=", date],
			"end_date": [">=", date],
		},
		"name"
	)
	if ay:
		return ay
	
	d = frappe.utils.getdate(date)
	start_year = d.year if d.month >= 4 else d.year - 1
	end_year = start_year + 1
	ay_name = f"{start_year}-{end_year}"
	
	if frappe.db.exists("Academic Year", ay_name):
		return ay_name
		
	return ay_name


@frappe.whitelist()
def make_admission_form(source_name, target_doc=None):
	enquiry = frappe.get_doc("Student Enquiry Form", source_name)
	
	adm_form = frappe.get_doc({
		"doctype": "Student Admission Form",
		"student_enquiry": enquiry.name,
		"academic_year": enquiry.academic_year,
		"standard": enquiry.standard,
		"student_name": enquiry.applicant_name,
		"gender": enquiry.gender,
		"date_of_birth": enquiry.date_of_birth,
		"school_name": enquiry.school_name,
		"father_name": enquiry.parent_name,
		# The enquiry holds a single parent contact; the admission form splits
		# it into father / mother, so carry it over as the father's number.
		"father_mobile_number": enquiry.parent_mobile,
		"address": enquiry.address,
		"application_date": frappe.utils.today()
	})
	return adm_form
