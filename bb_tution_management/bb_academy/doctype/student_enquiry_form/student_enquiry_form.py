# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint, flt, getdate

from bb_tution_management.bb_academy.doctype.fee_structure.fee_structure import (
	get_monthly_fee as get_fee_structure_monthly_fee,
)

# The enquiry's fee quote lives in its own fee_preview_* fields. They are named
# apart from the Admission Form's fee fields on purpose: get_mapped_doc copies
# same-named fields across, and the quote is only for showing the parents --
# the admission works its fees out afresh.
FEE_PREVIEW_FIELDS = (
	"fee_preview_starting_payment",
	"fee_preview_monthly_fee",
	"fee_preview_first_payment",
	"fee_preview_yearly_total",
	"fee_preview_yearly_savings",
)


class StudentEnquiryForm(Document):
	def validate(self):
		if not self.academic_year or self.standard:
			self.academic_year = get_academic_year(self.enquiry_date or frappe.utils.today(), self.standard)
		self.set_fee_preview()

	def set_fee_preview(self):
		preview = get_fee_preview(
			self.standard,
			self.fee_preview_batch,
			self.academic_year,
			self.fee_preview_joining_date or self.enquiry_date,
			self.fee_preview_yearly,
		)
		for field in FEE_PREVIEW_FIELDS:
			self.set(field, preview.get(field.replace("fee_preview_", ""), 0))


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
def get_fee_preview(standard=None, batch=None, academic_year=None, joining_date=None, yearly=0):
	"""What the parents would pay, quoted by the same rules the Admission Form
	bills by -- so the figure given at the enquiry is the one charged later.

	Monthly: the starting payment and the monthly fee, plus the rows due on the
	day they join. Yearly: the auto calculated yearly breakdown, its total, and
	what the free month saves against paying the same months one by one.

	Never throws: a quote that cannot be worked out yet comes back with a
	`message` saying why, so saving the enquiry is not held up by it.
	"""
	from bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice import get_academic_months
	from bb_tution_management.bb_academy.doctype.student_admission_form.student_admission_form import (
		NO_FEES,
		get_admission_fee_rows,
		get_yearly_fee_breakdown,
	)

	starting_payment = flt(frappe.db.get_value("Standard", standard, "starting_payment")) if standard else 0
	monthly_fee = flt(get_fee_structure_monthly_fee(standard, batch)) if batch else 0
	preview = frappe._dict(starting_payment=starting_payment, monthly_fee=monthly_fee, rows=[], notes=[])

	if not standard or not batch:
		preview.message = _("Select the Standard and Batch to see the fees.")
		return preview
	if not monthly_fee:
		preview.message = _("No Fee Structure is set up for Standard {0} and Batch {1}.").format(standard, batch)
		return preview
	if not get_academic_months(academic_year):
		preview.message = _("Academic Year {0} has no start and end date.").format(academic_year or "")
		return preview

	joining_date = getdate(joining_date or frappe.utils.today())
	if joining_date > getdate(frappe.db.get_value("Academic Year", academic_year, "end_date")):
		preview.message = _("Expected Joining Date is after Academic Year {0} ends.").format(academic_year)
		return preview

	if cint(yearly):
		rows = get_yearly_fee_breakdown(academic_year, joining_date, starting_payment, monthly_fee)
		preview.rows = rows
		preview.yearly_total = sum(flt(row.amount_need_to_pay) for row in rows)
		preview.yearly_savings = round(monthly_fee) * len([row for row in rows if row.status == NO_FEES])
	else:
		quote = get_admission_fee_rows(academic_year, joining_date, starting_payment, monthly_fee)
		preview.rows = quote["rows"]
		preview.notes = quote["notes"]
		preview.first_payment = sum(flt(row["amount_need_to_pay"]) for row in quote["rows"])

	return preview


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
		target.date_of_joining = source.fee_preview_joining_date or target.application_date
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
