# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, getdate

from bb_tution_management.bb_academy.doctype.fee_structure.fee_structure import get_monthly_fee
from bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice import update_student_totals


MONTH_NAMES = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December"
]

# Map month name -> 1-based month number
MONTH_NUMBER = {name: idx + 1 for idx, name in enumerate(MONTH_NAMES)}

# Editable fee field -> (field holding the reason for the change, fields the
# fee is normally derived from). Used by the "Edit Fees Amount" button.
EDITABLE_FEES = {
	"starting_payment": {
		"reason_field": "reason_for_discounting_starting_amount",
		"source_fields": ("standard",),
	},
	"monthly_fee": {
		"reason_field": "reason_for_discounting_monthly_fees",
		"source_fields": ("standard", "current_batch"),
	},
}


class Student(Document):
	def validate(self):
		self.fetch_academic_year()
		self.fetch_starting_payment()
		self.fetch_monthly_fee()
		self.populate_payment_details()
		self.update_scholarship_payment_details()
		update_student_totals(self)

	def before_save(self):
		self.track_batch_change()

	def update_scholarship_payment_details(self):
		"""When scholarship_student is checked, set all 'Not Paid' statuses in payment_details to 'Paid'."""
		if self.scholarship_student:
			for row in self.get("payment_details", []):
				if row.status == "Not Paid":
					row.status = "Paid"


	def after_insert(self):
		self.create_referral_coupon_code()

	def create_referral_coupon_code(self):
		if not self.referred_by:
			return

		if not frappe.db.exists("Student", self.referred_by):
			return

		referring_student = frappe.get_doc("Student", self.referred_by)

		academic_year_name = referring_student.academic_year or self.academic_year
		valid_till = None
		if academic_year_name:
			valid_till = frappe.db.get_value("Academic Year", academic_year_name, "end_date")

		coupon = frappe.get_doc({
			"doctype": "Referral Coupon Code",
			"student_id": referring_student.name,
			"student_name": referring_student.student_name,
			"amount": 500,
			"valid_till": valid_till,
		})
		coupon.insert(ignore_permissions=True)

		referring_student.append("coupon_code_details", {
			"referral_coupon_code": coupon.name,
			"valid_till": valid_till,
			"amount": 500,
		})
		referring_student.save(ignore_permissions=True)

	def populate_payment_details(self):
		"""Auto-populate payment_details months based on academic year and admission date.

		- Months before the student's admission_date month -> status "Not Joined"
		- Months from admission_date month onward          -> status "Not Paid"

		Only runs when the academic_year or admission_date has changed, or when
		the payment_details table is empty. Existing rows with status other than
		"Not Joined" / "Not Paid" (i.e. already Paid / Partial) are preserved.
		"""
		if not self.academic_year or not self.admission_date:
			return

		# ----- determine if we need to rebuild -----
		needs_rebuild = False

		if not self.payment_details:
			needs_rebuild = True

		if not self.is_new():
			doc_before = self.get_doc_before_save()
			if doc_before:
				if (doc_before.academic_year != self.academic_year
						or str(doc_before.admission_date) != str(self.admission_date)):
					needs_rebuild = True
		else:
			# New document – always populate
			needs_rebuild = True

		if not needs_rebuild:
			return

		# ----- fetch academic year start/end dates -----
		ay = frappe.get_cached_doc("Academic Year", self.academic_year)
		if not ay.start_date or not ay.end_date:
			return

		start_date = getdate(ay.start_date)
		end_date = getdate(ay.end_date)

		total_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
		if total_months <= 0:
			return

		# Build ordered list of month numbers from start_date to end_date
		# e.g. June(6) to March(3) -> [6,7,8,9,10,11,12,1,2,3]
		academic_months = []
		m = start_date.month
		for _ in range(total_months):
			academic_months.append(m)
			m = m % 12 + 1  # next month, wrapping Dec(12)->Jan(1)

		# ----- admission month -----
		ad_date = getdate(self.admission_date)
		admission_month_num = ad_date.month  # 1-based

		# ----- build a lookup of existing rows we want to keep -----
		existing = {}
		starting_payment_row = None
		for row in (self.payment_details or []):
			if row.month == "Starting Payment":
				starting_payment_row = row
				continue
			month_num = MONTH_NUMBER.get(row.month)
			if month_num and row.status not in (None, "", "Not Joined", "Not Paid"):
				# Preserve rows that have meaningful status (Paid, Partial, etc.)
				existing[month_num] = row

		# ----- rebuild the table -----
		self.payment_details = []
		
		# Add starting payment row if applicable
		if self.starting_payment:
			if starting_payment_row:
				self.append("payment_details", {
					"month": starting_payment_row.month,
					"date": starting_payment_row.date,
					"status": starting_payment_row.status,
					"amount_need_to_pay": starting_payment_row.amount_need_to_pay,
					"amount_paid": starting_payment_row.amount_paid,
					"pending": starting_payment_row.pending,
				})
			else:
				self.append("payment_details", {
					"month": "Starting Payment",
					"status": "Not Paid",
					"amount_need_to_pay": self.starting_payment,
					"pending": self.starting_payment
				})

		for month_num in academic_months:
			month_name = MONTH_NAMES[month_num - 1]

			if month_num in existing:
				# Keep the existing row data intact
				kept = existing[month_num]
				self.append("payment_details", {
					"month": kept.month,
					"date": kept.date,
					"status": kept.status,
					"amount_need_to_pay": kept.amount_need_to_pay,
					"amount_paid": kept.amount_paid,
					"pending": kept.pending,
				})
			else:
				# Determine if the student had joined by this month
				if month_num in academic_months:
					# Find position of this month and admission month in the
					# academic calendar to compare correctly across year boundary
					month_pos = academic_months.index(month_num)
					try:
						admission_pos = academic_months.index(admission_month_num)
					except ValueError:
						# Admission month not in academic calendar – treat as joined
						admission_pos = 0

					if month_pos < admission_pos:
						status = "Not Joined"
					else:
						status = "Not Paid"
				else:
					status = "Not Paid"

				self.append("payment_details", {
					"month": month_name,
					"status": status,
				})

	def create_starting_fee_invoice(self):
		if not self.starting_payment:
			return

		# Check if starting fee invoice already exists
		existing = frappe.db.exists(
			"Fee Invoice",
			{
				"student": self.name,
				"is_starting_fee": 1,
				"docstatus": ["!=", 2]
			}
		)
		if existing:
			return

		from frappe.utils import today, add_days
		ad_date = getdate(self.admission_date or today())
		invoice = frappe.get_doc({
			"doctype": "Fee Invoice",
			"student": self.name,
			"fee_month": "Starting Payment",
			"invoice_date": today(),
			"due_date": add_days(today(), 10),
			"is_starting_fee": 1,
			"monthly_fee": self.starting_payment
		})
		invoice.insert(ignore_permissions=True)
		invoice.submit()

	def has_manual_fee(self, fee_field):
		"""True when this fee was set by hand via "Edit Fees Amount" and should
		not be pulled back from the Standard / Fee Structure.

		The override is dropped as soon as one of the fields the fee is derived
		from changes -- a discount agreed for one standard/batch does not carry
		over to another.
		"""
		if self.flags.get("ignore_fee_fetch"):
			return True

		config = EDITABLE_FEES[fee_field]
		if not self.get(config["reason_field"]):
			return False

		doc_before = None if self.is_new() else self.get_doc_before_save()
		if not doc_before:
			return False

		return all(doc_before.get(f) == self.get(f) for f in config["source_fields"])

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

	def fetch_starting_payment(self):
		if not self.standard:
			return

		if self.has_manual_fee("starting_payment"):
			return

		# Any manual amount has been superseded -- drop the reason that went with it.
		self.reason_for_discounting_starting_amount = None

		starting_payment = frappe.db.get_value("Standard", self.standard, "starting_payment")
		if starting_payment is not None:
			self.starting_payment = starting_payment

	def fetch_monthly_fee(self):
		if not (self.standard and self.current_batch):
			return

		if self.has_manual_fee("monthly_fee"):
			return

		# Any manual amount has been superseded -- drop the reason that went with it.
		self.reason_for_discounting_monthly_fees = None

		# "standard" on Fee Structure is a Table MultiSelect, so it lives in
		# the Standard Detail child table, not as a column on tabFee Structure.
		monthly_fee = get_monthly_fee(self.standard, self.current_batch)
		if monthly_fee is not None:
			self.monthly_fee = monthly_fee

	def track_batch_change(self):
		if self.is_new() or getattr(self.flags, "ignore_batch_history", False):
			return

		doc_before_save = self.get_doc_before_save()
		if not doc_before_save or doc_before_save.current_batch == self.current_batch:
			return

		previous_batch = doc_before_save.current_batch
		new_batch = self.current_batch

		# Both batches are required on a transition, so a student being moved
		# into their first batch has nothing to record.
		if not (previous_batch and new_batch):
			return

		transition = frappe.get_doc({
			"doctype": "Student Batch Transition",
			"student": self.name,
			"previous_batch": previous_batch,
			"new_batch": new_batch,
			"effective_date": frappe.utils.today(),
			"reason": _("Batch updated for student {0} from {1} to {2} by {3}").format(
				self.student_name, previous_batch, new_batch, frappe.session.user
			),
		})
		# The batch is already being changed on this document -- don't let the
		# transition turn around and save the Student again.
		transition.flags.ignore_student_update = True
		transition.insert(ignore_permissions=True)

		frappe.msgprint(
			_("Student batch change recorded in Student Batch Transition {0}, from {1} to {2}.").format(
				frappe.utils.get_link_to_form("Student Batch Transition", transition.name),
				previous_batch,
				new_batch,
			)
		)


@frappe.whitelist()
def get_editable_fees(student):
	"""Current fee amounts and the reason recorded against each, for the
	"Edit Fees Amount" dialog."""
	doc = frappe.get_doc("Student", student)
	doc.check_permission("read")

	return {
		fee_field: {
			"amount": flt(doc.get(fee_field)),
			"reason": doc.get(config["reason_field"]),
		}
		for fee_field, config in EDITABLE_FEES.items()
	}


@frappe.whitelist()
def update_fee_amount(student, fee_type, new_amount, reason):
	"""Set the starting payment or monthly fee on a Student to a manually
	agreed amount, recording why it was changed."""
	config = EDITABLE_FEES.get(fee_type)
	if not config:
		frappe.throw(_("{0} is not an editable fee.").format(fee_type))

	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("A reason is required to change the fees amount."))

	new_amount = flt(new_amount)
	if new_amount < 0:
		frappe.throw(_("Fees amount cannot be negative."))

	doc = frappe.get_doc("Student", student)
	doc.check_permission("write")

	old_amount = flt(doc.get(fee_type))
	doc.set(fee_type, new_amount)
	doc.set(config["reason_field"], reason)

	# Keep validate() from pulling the amount back from the Standard / Fee Structure.
	doc.flags.ignore_fee_fetch = True
	doc.save()

	return {
		"fee_type": fee_type,
		"old_amount": old_amount,
		"new_amount": flt(doc.get(fee_type)),
		"reason": reason,
	}

@frappe.whitelist()
def get_academic_year_for_standard(standard):
	if not standard:
		return None

	active_academic_years = frappe.get_all("Academic Year", filters={"is_active": 1}, pluck="name")
	if not active_academic_years:
		return None

	academic_year = frappe.db.get_value(
		"Standard Detail",
		{
			"parent": ["in", active_academic_years],
			"parenttype": "Academic Year",
			"parentfield": "standard_applicable",
			"standard": standard
		},
		"parent"
	)
	return academic_year


def check_attendance_batch_expiry():
	"""
	Check all students with attendance_batch_set=1.
	If today is past attendance_batch_end_date, reset the flags and clear the dates.
	"""
	from frappe.utils import today, getdate
	current_date = getdate(today())
	
	students_to_reset = frappe.get_all(
		"Student",
		filters={
			"attendance_batch_set": 1,
			"attendance_batch_end_date": ["<", current_date]
		}
	)
	
	for student in students_to_reset:
		doc = frappe.get_doc("Student", student.name)
		doc.attendance_batch_set = 0
		doc.attendance_batch = None
		doc.attendance_batch_start_date = None
		doc.attendance_batch_end_date = None
		# Skip tracking batch change or fee updates for this background task if possible
		doc.flags.ignore_batch_history = True
		doc.flags.ignore_fee_fetch = True
		doc.save(ignore_permissions=True)


