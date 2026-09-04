# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint, flt

from bb_tution_management.bb_academy.doctype.fee_structure.fee_structure import (
	get_monthly_fee as get_fee_structure_monthly_fee,
)
from bb_tution_management.bb_tution_management.doctype.group.group import get_groups_for_standard

# A Group (Science / Commerce / Bio Maths ...) only applies to higher standards.
# Standards with academic_order above this are the ones that carry Groups.
GROUP_MIN_ACADEMIC_ORDER = 5


def standard_takes_group(standard):
	"""True if the given Standard is senior enough to have a Group."""
	if not standard:
		return False

	academic_order = frappe.db.get_value("Standard", standard, "academic_order")
	return cint(academic_order) > GROUP_MIN_ACADEMIC_ORDER


class StudentAdmissionForm(Document):
	def validate(self):
		self.fetch_academic_year()
		if not self.admission_number:
			from frappe.model.naming import make_autoname
			year = str(frappe.utils.getdate(self.application_date or frappe.utils.today()).year)
			self.admission_number = make_autoname(f"BB-{year}-.####")

		self.set_standard_academic_order()
		self.validate_group()
		self.fetch_fees()
		self.validate_admission_number()
		self.validate_discount_amount()

	def before_submit(self):
		self.validate_payment_method()
		self.validate_fees_paid()

	def validate_discount_amount(self):
		if self.add_discount:
			total_discount = sum(flt(row.discount_amount) for row in self.get("fees__invoice_details", []))
			if total_discount > 0:
				limit = flt(frappe.db.get_single_value("BB Academy Settings", "discount_amount_limit"))
				if limit and total_discount > limit:
					frappe.throw(_("Total Discount Amount ({0}) cannot exceed the limit of {1}.").format(total_discount, limit))

	def validate_payment_method(self):
		if not self.payment_method:
			frappe.throw(_("Payment Method is mandatory before submitting."))

		if self.is_yearly_payment:
			total_paid = flt(self.yearly_fees_paid_amount)
		else:
			total_paid = sum(flt(row.paid_amount) for row in self.get("fees__invoice_details"))

		if self.payment_method == "Split Up":
			split_total = flt(self.cash) + flt(self.gpay) + flt(self.scanner)
			if abs(split_total - total_paid) > 0.01:
				frappe.throw(_("For 'Split Up' payment method, the sum of Cash, GPAY, and Scanner ({0}) must equal the Total Paid Amount ({1}).").format(split_total, total_paid))

	def validate_fees_paid(self):
		if self.is_new():
			return
		if self.is_yearly_payment:
			if not self.total_year_payment_amount:
				frappe.throw(_("Total Year Payment Amount is mandatory for Yearly Payment."))
			return

		if self.starting_payment:
			min_required = flt(self.starting_payment) * 0.5
			paid_amount = sum(flt(row.paid_amount) for row in self.get("fees__invoice_details"))
			if paid_amount < min_required:
				frappe.throw(_("Fees Paid Amount must be at least 50% of the Starting Payment (Minimum: {0})").format(min_required))

	def fetch_academic_year(self):
		if not self.standard:
			self.academic_year = None
			return

		active_academic_years = frappe.get_all("Academic Year", filters={"is_active": 1}, pluck="name")
		if not active_academic_years:
			return

		academic_year = frappe.db.get_value(
			"Standard Detail",
			{
				"parent": ["in", active_academic_years],
				"parenttype": "Academic Year",
				"parentfield": "standard_applicable",
				"standard": self.standard
			},
			"parent"
		)

		if academic_year:
			self.academic_year = academic_year

	def set_standard_academic_order(self):
		"""Mirror the Standard's academic_order onto the form.

		The Group field's depends_on reads this, in the desk form and in the
		web form alike, so it has to be present on the document itself.
		"""
		if not self.standard:
			self.standard_academic_order = 0
			return

		self.standard_academic_order = cint(
			frappe.db.get_value("Standard", self.standard, "academic_order")
		)

	def validate_group(self):
		"""A Group is only allowed on senior standards, and only if mapped to it."""
		if not self.group:
			return

		if not standard_takes_group(self.standard):
			# The Group field is hidden for these standards -- drop any stale value
			# rather than blocking the admission over an invisible field.
			self.group = None
			return

		allowed_groups = get_groups_for_standard(self.standard)
		# link values are compared case-insensitively by the database, so don't be
		# stricter here than the Link field itself is
		if self.group.casefold() not in {g.casefold() for g in allowed_groups}:
			frappe.throw(
				_("Group {0} is not available for Standard {1}.").format(
					frappe.bold(self.group), frappe.bold(self.standard)
				)
				+ "<br><br>"
				+ (
					_("Available groups: {0}").format(frappe.bold(", ".join(allowed_groups)))
					if allowed_groups
					else _("No group is mapped to this standard yet.")
				),
				title=_("Invalid Group"),
			)

	def fetch_fees(self):
		if self.standard:
			starting_payment = frappe.db.get_value("Standard", self.standard, "starting_payment")
			if starting_payment is not None and not self.starting_payment:
				self.starting_payment = starting_payment

		if self.standard and self.assigned_batch:
			monthly_fee = get_monthly_fee(self.standard, self.assigned_batch)
			if monthly_fee is not None:
				self.monthly_fee = monthly_fee

	def validate_admission_number(self):
		if self.admission_number:
			existing_student = frappe.db.exists("Student", {"admission_number": self.admission_number})
			if existing_student:
				frappe.throw(_("A Student already exists with Admission Number '{0}'.").format(self.admission_number))

	def on_submit(self):
		self.create_student_record()
		self.update_enquiry_status()
		self.create_fee_invoice()

	def create_fee_invoice(self):
		if not self.starting_payment and not self.is_yearly_payment:
			return

		student_name = frappe.db.get_value("Student", {"admission_number": self.admission_number}, "name")
		if not student_name:
			return

		try:
			invoice = frappe.get_doc({
				"doctype": "Fee Invoice",
				"student": student_name,
				"invoice_date": frappe.utils.today(),
				"is_starting_fee": 0 if self.is_yearly_payment else 1,
				"yearly_fees_student": 1 if self.is_yearly_payment else 0,
				"monthly_fee": self.starting_payment if not self.is_yearly_payment else self.total_year_payment_amount,
				"paid_amount": flt(self.yearly_fees_paid_amount) if self.is_yearly_payment else sum(flt(row.paid_amount) for row in self.get("fees__invoice_details")),
				"payment_method": self.payment_method,
				"cash": self.cash if self.payment_method == "Split Up" else 0,
				"gpay": self.gpay if self.payment_method == "Split Up" else 0,
				"scanner": self.scanner if self.payment_method == "Split Up" else 0,
				"add_discount": self.add_discount,
				"discount_amount": sum(flt(r.discount_amount) for r in self.get("fees__invoice_details", [])) if self.add_discount else 0.0,
				"fees_details": []
			})
			if not self.is_yearly_payment:
				for row in self.get("fees__invoice_details"):
					invoice.append("fees_details", {
						"month": row.month,
						"amount_need_to_pay": row.amount_need_to_pay,
						"paid_amount": row.paid_amount,
						"discount_amount": row.discount_amount
					})
			invoice.insert(ignore_permissions=True)
			invoice.submit()
			frappe.msgprint(
				_("Fee Invoice {0} created and submitted successfully for {1}.").format(
					frappe.bold(invoice.name), frappe.bold(self.student_name)
				),
				indicator="green"
			)
		except Exception:
			frappe.log_error(
				title=f"Fee Invoice creation failed for Admission {self.name}",
				message=frappe.get_traceback(with_context=True),
			)
			frappe.throw(
				_("Could not create the Fee Invoice for {0}. The admission has not been fully processed.").format(
					frappe.bold(self.student_name or self.name)
				)
			)

	def create_student_record(self):
		if not self.admission_number:
			from frappe.model.naming import make_autoname
			year = str(frappe.utils.getdate(self.application_date or frappe.utils.today()).year)
			self.admission_number = make_autoname(f"BB-{year}-.####")
			self.db_set("admission_number", self.admission_number)

		existing_student = frappe.db.exists("Student", {"admission_number": self.admission_number})
		if existing_student:
			frappe.msgprint(
				_("Student {0} already exists for Admission Number {1}. No new record was created.").format(
					frappe.bold(existing_student), frappe.bold(self.admission_number)
				),
				title=_("Student Already Exists"),
				indicator="orange",
			)
			return

		try:
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
				"school_name": self.school_name,
				"address": self.address,
				"starting_payment": self.starting_payment,
				"monthly_fee": self.monthly_fee,
				"referred_by": self.referred_by_student_id,
				"yearly_fees_student": 1 if self.is_yearly_payment else 0,
				"yearly_fees_amount": self.total_year_payment_amount if self.is_yearly_payment else 0,
				"yearly_fees_pending_amount": flt(self.total_year_payment_amount) if self.is_yearly_payment else 0,
				"status": "Active"
			})
			student.insert(ignore_permissions=True)
		except frappe.ValidationError:
			raise
		except Exception:
			frappe.log_error(
				title=f"Student creation failed for Admission {self.name}",
				message=frappe.get_traceback(with_context=True),
			)
			frappe.throw(
				_("Could not create the Student record for {0}. The admission has not been submitted.<br><br>"
				  "The technical details have been saved to the Error Log for the administrator.").format(
					frappe.bold(self.student_name or self.name)
				),
				title=_("Student Creation Failed"),
			)

		frappe.msgprint(
			_("Student {0} created successfully for {1}.").format(
				frappe.bold(student.name), frappe.bold(self.student_name)
			),
			title=_("Admission Approved"),
			indicator="green",
		)

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
		if not self.student_enquiry:
			return

		if not frappe.db.exists("Student Enquiry Form", self.student_enquiry):
			frappe.msgprint(
				_("Linked Student Enquiry {0} no longer exists, so its status was not updated.").format(
					frappe.bold(self.student_enquiry)
				),
				indicator="orange",
			)
			return

		frappe.db.set_value("Student Enquiry Form", self.student_enquiry, "status", "Converted")

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_standard_ordered(doctype, txt, searchfield, start, page_len, filters):
	"""Link-field query: active Standards in academic order.

	The parameter names/order are fixed by frappe.desk.search.search_widget,
	which calls this positionally as (doctype, txt, searchfield, start,
	page_len, filters).
	"""
	return frappe.db.sql(
		"""
		select name, standard_name
		from `tabStandard`
		where is_active = 1 and name like %(txt)s
		order by academic_order asc
		limit %(start)s, %(page_len)s
		""",
		{
			"txt": f"%{txt or ''}%",
			"start": cint(start),
			"page_len": cint(page_len) or 10,
		},
	)


@frappe.whitelist(allow_guest=True)
def get_admission_form_options(standard=None):
	"""Standard/Group options for the public admission web form.

	The web form at /admission is open to Guests, and frappe.desk.search.search_link
	is not guest-whitelisted -- so Link autocomplete returns nothing there. The web
	form therefore renders these two fields as Select and fills them from here.
	"""
	standards = frappe.get_all(
		"Standard",
		filters={"is_active": 1},
		fields=["name", "academic_order"],
		order_by="academic_order asc",
	)

	return {
		"standards": [
			{"value": d.name, "academic_order": cint(d.academic_order)} for d in standards
		],
		"group_min_academic_order": GROUP_MIN_ACADEMIC_ORDER,
		"groups": get_groups_for_standard(standard) if standard else [],
		"show_group": standard_takes_group(standard),
	}


@frappe.whitelist()
def get_monthly_fee(standard, batch):
	return get_fee_structure_monthly_fee(standard, batch) or 0

@frappe.whitelist(allow_guest=True)
def get_enquiry_details(enquiry_name):
	if not frappe.db.exists("Student Enquiry Form", enquiry_name):
		return {}
	
	doc = frappe.get_doc("Student Enquiry Form", enquiry_name)
	return {
		"student_enquiry": doc.name,
		"student_name": doc.applicant_name,
		"gender": doc.gender,
		"date_of_birth": doc.date_of_birth,
		"school_name": doc.school_name,
		"referred_by": doc.referred_by,
		"standard": doc.standard,
		"group": doc.group,
		"parent_mobile": doc.parent_mobile,
		"father_name": doc.father_name,
		"mother_name": doc.mother_name,
		"father_mobile_number": doc.father_number,
		"mother_mobile_number": doc.mother_number
	}
