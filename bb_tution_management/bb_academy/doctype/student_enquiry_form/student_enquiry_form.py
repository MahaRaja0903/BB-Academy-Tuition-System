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
	from frappe.model.mapper import get_mapped_doc

	# One enquiry becomes one admission -- send staff to the existing one
	# rather than letting a second draft pile up.
	existing = frappe.db.get_value(
		"Student Admission Form",
		{"student_enquiry": source_name, "docstatus": ["<", 2]},
		"name",
	)
	if existing:
		frappe.throw(
			_("Admission Form {0} already exists for this enquiry.").format(
				frappe.utils.get_link_to_form("Student Admission Form", existing)
			),
			title=_("Admission Already Created"),
		)

	def set_missing_values(source, target):
		target.student_enquiry = source.name
		target.application_date = frappe.utils.today()
		if source.standard and not target.starting_payment:
			target.starting_payment = frappe.db.get_value("Standard", source.standard, "starting_payment")

	return get_mapped_doc(
		"Student Enquiry Form",
		source_name,
		{
			"Student Enquiry Form": {
				"doctype": "Student Admission Form",
				"field_map": {
					"applicant_name": "student_name",
					"father_number": "father_mobile_number",
					"mother_number": "mother_mobile_number",
					"guardian_number": "guardian_mobile_number",
					"street": "street_name",
				},
				"field_no_map": ["naming_series", "status"],
			},
		},
		target_doc,
		set_missing_values,
	)

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
