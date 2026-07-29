# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class StudentEnquiryForm(Document):
	def validate(self):
		pass


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
		"parent_mobile": enquiry.parent_mobile,
		"whatsapp_number": enquiry.parent_mobile,
		"address": enquiry.address,
		"application_date": frappe.utils.today()
	})
	return adm_form
