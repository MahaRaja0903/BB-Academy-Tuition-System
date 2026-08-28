# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class StudentEnquiryForm(Document):
	def validate(self):
		if not self.academic_year or self.standard:
			self.academic_year = get_academic_year(self.enquiry_date or frappe.utils.today(), self.standard)


@frappe.whitelist()
def get_academic_year(date=None, standard=None):
	if not date:
		date = frappe.utils.today()
	
	if standard:
		query = """
			SELECT p.name 
			FROM `tabAcademic Year` p
			JOIN `tabStandard Detail` c ON p.name = c.parent
			WHERE c.standard = %s 
			AND p.start_date <= %s 
			AND p.end_date >= %s
			LIMIT 1
		"""
		ay = frappe.db.sql(query, (standard, date, date))
		if ay:
			return ay[0][0]

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
		"father_name": enquiry.father_name,
		"mother_name": enquiry.mother_name,
		"father_mobile_number": enquiry.father_number,
		"mother_mobile_number": enquiry.mother_number,
		"address": enquiry.get("address") if hasattr(enquiry, "address") else None,
		"application_date": frappe.utils.today()
	})
	return adm_form

@frappe.whitelist()
def get_short_url(long_url):
	import requests
	try:
		response = requests.get(f"https://tinyurl.com/api-create.php?url={long_url}", timeout=5)
		if response.status_code == 200:
			return response.text
	except Exception:
		pass
	return long_url
