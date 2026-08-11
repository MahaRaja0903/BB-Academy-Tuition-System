# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

from calendar import monthrange

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, getdate, nowdate

MONTH_NAMES = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December"
]

MONTH_NUMBER = {name: idx + 1 for idx, name in enumerate(MONTH_NAMES)}

STARTING_PAYMENT = "Starting Payment"

# A student who joins on or before this day of the month is billed for the whole
# month; joining later is billed only for the days that are left in the month.
PRORATA_CUTOFF_DAY = 10


def get_academic_months(academic_year):
	"""Month names of an academic year, in calendar order from its start month.

	e.g. an April -> March year gives [April, May, ... February, March].
	"""
	if not academic_year:
		return []

	ay = frappe.get_cached_doc("Academic Year", academic_year)
	start_month = MONTH_NUMBER.get(ay.start_month)
	end_month = MONTH_NUMBER.get(ay.end_month)
	if not start_month or not end_month:
		return []

	months = []
	m = start_month
	while True:
		months.append(MONTH_NAMES[m - 1])
		if m == end_month:
			break
		m = m % 12 + 1  # next month, wrapping Dec(12) -> Jan(1)

	return months


def get_join_date(student_doc):
	"""The date the days-based rules are measured from."""
	return getdate(student_doc.admission_date) if student_doc.admission_date else getdate(nowdate())


def get_payment_row(student_doc, month):
	for row in student_doc.get("payment_details", []):
		if row.month == month:
			return row
	return None


def is_prorated_month(student_doc, month):
	"""True for the joining month of a student who joined after the cutoff day.

	That month is only partly attended, so it is billed by the day instead of at
	the full monthly fee.
	"""
	if month == STARTING_PAYMENT:
		return False

	join_date = get_join_date(student_doc)
	return (
		join_date.day > PRORATA_CUTOFF_DAY
		and month == MONTH_NAMES[join_date.month - 1]
	)


def get_prorated_amount(monthly_fee, join_date):
	"""Monthly fee charged only for the days remaining in the joining month."""
	join_date = getdate(join_date)
	days_in_month = monthrange(join_date.year, join_date.month)[1]
	remaining_days = days_in_month - join_date.day + 1

	return flt(monthly_fee) * remaining_days / days_in_month


def get_month_amount(student_doc, month):
	"""Full amount billable to a student for one Fees Details row."""
	if month == STARTING_PAYMENT:
		return round(flt(student_doc.starting_payment or 0))

	monthly_fee = flt(student_doc.monthly_fee or 0)
	if is_prorated_month(student_doc, month):
		return round(get_prorated_amount(monthly_fee, get_join_date(student_doc)))

	return round(monthly_fee)


def get_row_default_amount(student_doc, month):
	"""What is still owed for a month -- what a new invoice row should ask for."""
	amount = get_month_amount(student_doc, month)

	row = get_payment_row(student_doc, month)
	if row:
		amount -= flt(row.amount_paid)

	return max(0, round(amount))


def get_advance_months(student_doc):
	"""The two months the starting payment pays for in advance.

	The starting payment covers the student's first *full* month and the last
	month of the academic year. A student who joined after the cutoff day pays
	their joining month pro-rata instead, so their first full month -- and hence
	what the advance covers -- is the month after that.
	"""
	months = get_academic_months(student_doc.academic_year)
	if not months:
		return None, None

	join_date = get_join_date(student_doc)
	join_month = MONTH_NAMES[join_date.month - 1]

	first_index = 0
	if join_month in months:
		first_index = months.index(join_month)
		if join_date.day > PRORATA_CUTOFF_DAY:
			first_index += 1

	if first_index >= len(months):
		# Joined in the last month of the year, after the cutoff -- nothing left
		# for the advance to cover as a first month.
		return None, months[-1]

	first_month = months[first_index]
	last_month = months[-1]

	return first_month, (last_month if last_month != first_month else None)


def should_bill_month(student_doc, month, starting_pending):
	"""Whether a month still needs to appear on a new invoice."""
	months = get_academic_months(student_doc.academic_year)
	if months and month not in months:
		return False

	row = get_payment_row(student_doc, month)
	if row and row.status in ("Paid", "Not Joined"):
		return False

	# While the starting payment is outstanding the months it pays for in
	# advance must not also be billed on their own.
	if starting_pending > 0 and month in get_advance_months(student_doc):
		return False

	return get_row_default_amount(student_doc, month) > 0


def get_coupon_codes(invoice):
	"""The coupon codes on an invoice, stored as a comma separated list."""
	return [code.strip() for code in (invoice.coupon__code or "").split(",") if code.strip()]


def is_coupon_available(row, today=None):
	"""A referral coupon can be redeemed while it is unused and not past its
	validity date."""
	if not row.referral_coupon_code or row.used:
		return False

	if row.valid_till and getdate(row.valid_till) < (today or getdate(nowdate())):
		return False

	return True


@frappe.whitelist()
def get_available_coupons(student):
	"""Referral coupons on a student that can still be redeemed, for the
	"Add Coupon" picker."""
	student_doc = frappe.get_doc("Student", student)
	student_doc.check_permission("read")

	today = getdate(nowdate())

	return [
		{
			"coupon_code": row.referral_coupon_code,
			"amount": flt(row.amount),
			"valid_till": str(row.valid_till) if row.valid_till else None,
		}
		for row in student_doc.get("coupon_code_details", [])
		if is_coupon_available(row, today)
	]


@frappe.whitelist()
def get_student_fee_data(student):
	"""Return student info + payment_details for fee tracking UI."""
	student_doc = frappe.get_doc("Student", student)
	payment_rows = []
	for row in student_doc.get("payment_details", []):
		payment_rows.append({
			"month": row.month,
			"date": str(row.date) if row.date else None,
			"status": row.status,
			"amount_need_to_pay": float(row.amount_need_to_pay or 0),
			"amount_paid": float(row.amount_paid or 0),
			"pending": float(row.pending or 0),
		})

	# Amount a fresh invoice row should ask for, per month -- lets the client
	# fill the grid without a round trip for every row the user adds.
	academic_months = get_academic_months(student_doc.academic_year)
	row_amounts = {
		month: get_row_default_amount(student_doc, month)
		for month in [STARTING_PAYMENT] + academic_months
	}

	first_month, last_month = get_advance_months(student_doc)

	return {
		"student_name": student_doc.student_name,
		"admission_date": str(student_doc.admission_date) if student_doc.admission_date else None,
		"standard": student_doc.standard,
		"current_batch": student_doc.current_batch,
		"academic_year": student_doc.academic_year or "Current",
		"image": student_doc.image,
		"monthly_fee": float(student_doc.monthly_fee or 0),
		"starting_payment": float(student_doc.starting_payment or 0),
		"fees_due_date": student_doc.fees_due_date,
		"payment_details": payment_rows,
		"academic_months": academic_months,
		"row_amounts": row_amounts,
		"advance_months": [m for m in (first_month, last_month) if m],
		"total_paid_amount": float(student_doc.total_paid_amount or 0),
		"total_pending_amount": float(student_doc.total_pending_amount or 0),
	}


@frappe.whitelist()
def get_invoice_prefill(student):
	"""Rows to seed the Fees Details grid of a new invoice.

	Any outstanding starting payment, plus the current month unless it is
	already paid or covered by the starting payment advance. The joining month
	of a student who joined after the cutoff day is billed by the day.
	"""
	student_doc = frappe.get_doc("Student", student)
	student_doc.check_permission("read")

	rows = []
	notes = []

	starting_pending = get_row_default_amount(student_doc, STARTING_PAYMENT)
	if starting_pending > 0:
		rows.append({
			"month": STARTING_PAYMENT,
			"amount_need_to_pay": starting_pending,
			"paid_amount": starting_pending,
		})

		first_month, last_month = get_advance_months(student_doc)
		advance = ", ".join(m for m in (first_month, last_month) if m)
		if advance:
			notes.append(
				_("Paying the starting payment in full also settles {0}.").format(advance)
			)

	current_month = MONTH_NAMES[getdate(nowdate()).month - 1]
	if should_bill_month(student_doc, current_month, starting_pending):
		amount = get_row_default_amount(student_doc, current_month)
		rows.append({
			"month": current_month,
			"amount_need_to_pay": amount,
			"paid_amount": amount,
		})

		if is_prorated_month(student_doc, current_month):
			join_date = get_join_date(student_doc)
			days_in_month = monthrange(join_date.year, join_date.month)[1]
			notes.append(
				_("{0} is billed for {1} of {2} days, from the admission date {3}.").format(
					current_month,
					days_in_month - join_date.day + 1,
					days_in_month,
					frappe.format_value(join_date, {"fieldtype": "Date"}),
				)
			)

	return {
		"rows": rows,
		"has_starting_payment": 1 if starting_pending > 0 else 0,
		"notes": notes,
	}


class FeeInvoice(Document):
	def validate(self):
		self.set_row_amounts()
		self.validate_duplicate_rows()
		self.validate_duplicate_invoice()
		self.validate_coupons()
		self.calculate_outstanding()
		# self.update_status()

	def validate_coupons(self):
		"""Re-derive coupon_amount from the codes, against the student's own
		coupons -- never from whatever the client sent."""
		codes = get_coupon_codes(self)
		if not codes:
			self.coupon__code = None
			self.coupon_amount = 0
			return

		if not self.student:
			frappe.throw(_("Select a Student before applying a coupon."))

		student_doc = frappe.get_doc("Student", self.student)
		coupon_rows = {
			row.referral_coupon_code: row
			for row in student_doc.get("coupon_code_details", [])
			if row.referral_coupon_code
		}

		today = getdate(nowdate())
		total = 0.0
		seen = []

		for code in codes:
			if code in seen:
				frappe.throw(_("Coupon {0} is applied more than once.").format(code))
			seen.append(code)

			row = coupon_rows.get(code)
			if not row:
				frappe.throw(
					_("Coupon {0} does not belong to Student {1}.").format(code, self.student)
				)

			# On a submitted invoice the coupon is legitimately marked used -- by
			# this very invoice -- so only hold a draft to that rule.
			if row.used and self.docstatus == 0:
				if row.used_date:
					frappe.throw(_("Coupon {0} was already used on {1}.").format(
						code, frappe.format_value(row.used_date, {"fieldtype": "Date"})
					))
				frappe.throw(_("Coupon {0} has already been used.").format(code))

			if row.valid_till and getdate(row.valid_till) < today:
				frappe.throw(
					_("Coupon {0} expired on {1}.").format(
						code, frappe.format_value(row.valid_till, {"fieldtype": "Date"})
					)
				)

			claimed_by = frappe.db.sql("""
				select name from `tabFee Invoice`
				where docstatus != 2 and name != %s and find_in_set(%s, coupon__code)
			""", (self.name or "", code))

			if claimed_by:
				frappe.throw(
					_("Coupon {0} is already applied on Fee Invoice {1}.").format(code, claimed_by[0][0])
				)

			total += flt(row.amount)

		# Stored without spaces so find_in_set() above can match a single code.
		self.coupon__code = ",".join(seen)
		self.coupon_amount = total

	def set_row_amounts(self):
		"""Fill in what each row is billed for, so the grid never relies on the
		client having computed it."""
		if not self.student:
			return

		student_doc = frappe.get_doc("Student", self.student)
		for row in self.get("fees_details", []):
			if not row.month:
				continue

			if not row.amount_need_to_pay:
				row.amount_need_to_pay = get_row_default_amount(student_doc, row.month)

			if flt(row.paid_amount) > flt(row.amount_need_to_pay):
				frappe.throw(
					_("Row {0}: Paid Amount ({1}) cannot be more than the Amount Need to Pay ({2}) for {3}.").format(
						row.idx, row.paid_amount, row.amount_need_to_pay, row.month
					)
				)

	def validate_duplicate_rows(self):
		seen = set()
		for row in self.get("fees_details", []):
			if not row.month:
				continue
			if row.month in seen:
				frappe.throw(
					_("{0} appears more than once in Fees Details.").format(row.month)
				)
			seen.add(row.month)

	def validate_duplicate_invoice(self):
		if not self.student:
			return

		for detail in self.get("fees_details", []):
			month = detail.month
			if not month or month == STARTING_PAYMENT:
				continue

			existing = frappe.db.sql("""
				select parent from `tabFees Invoice Details`
				where month = %s and parenttype = 'Fee Invoice' and parent != %s
				and parent in (
					select name from `tabFee Invoice` where student = %s and docstatus != 2
				)
			""", (month, self.name or "", self.student))

			if existing:
				frappe.throw(
					_("A Fee Invoice ({0}) already exists for Student {1} for {2}.").format(
						existing[0][0], self.student, month
					)
				)

	def calculate_outstanding(self):
		if self.get("fees_details"):
			total_fee = 0.0
			total_paid = 0.0

			for row in self.fees_details:
				if not row.month:
					continue
				total_fee += flt(row.amount_need_to_pay)
				total_paid += flt(row.paid_amount)

			self.monthly_fee = total_fee
			self.paid_amount = total_paid

		discount = flt(self.discount_amount) if self.add_discount else 0.0
		net_total = flt(self.monthly_fee) - discount

		if self.apply_gst_18:
			self.gst_amount = net_total * 0.18
		else:
			self.gst_amount = 0.0

		self.grand_total = net_total + self.gst_amount
		final_total = self.grand_total + flt(self.outstanding_amount)
		self.balance_amount = max(0.0, final_total - flt(self.paid_amount))

		# A coupon is a credit against the payment, not a reduction of the fees:
		# the months are settled in full and the student hands over the rest.
		if flt(self.coupon_amount) > flt(self.paid_amount):
			frappe.throw(
				_("Coupon Amount ({0}) cannot be more than the Paid Amount ({1}).").format(
					self.coupon_amount, self.paid_amount
				)
			)

	@property
	def cash_to_collect(self):
		return max(0.0, flt(self.paid_amount) - flt(self.coupon_amount))

	# def update_status(self):
	# 	if self.docstatus == 2:
	# 		self.status = "Cancelled"
	# 	elif self.docstatus == 1:
	# 		if self.outstanding_amount <= 0:
	# 			self.status = "Paid"
	# 		elif float(self.paid_amount or 0) > 0:
	# 			self.status = "Partially Paid"
	# 		# else:
	# 		# 	self.status = "Unpaid"
	# 	else:
	# 		if not self.status:
	# 			self.status = "Draft"

	def on_submit(self):
		# We don't reset paid_amount here since Payment Entry is removed.
		# We just directly add the row to payment_details table
		self.update_student_payment_detail(is_submit=True)
		self.send_receipt_sms()

	def on_cancel(self):
		self.update_student_payment_detail(is_submit=False)

	def update_student_payment_detail(self, is_submit=True):
		student = frappe.get_doc("Student", self.student)
		sign = 1 if is_submit else -1

		for detail in self.get("fees_details", []):
			month = detail.month
			if not month:
				continue

			row = get_payment_row(student, month)
			if not row:
				row = student.append("payment_details", {"month": month, "amount_paid": 0.0})

			detail_paid = flt(detail.paid_amount)
			if detail_paid == 0 and len(self.get("fees_details", [])) == 1:
				detail_paid = flt(self.paid_amount)

			row.amount_paid = max(0.0, flt(row.amount_paid) + sign * detail_paid)
			row.date = frappe.utils.today() if is_submit else None

			# The starting payment is always measured against its full amount; a
			# monthly row keeps whatever it was actually billed, so a pro-rated
			# joining month is not later re-measured against the full fee.
			if month == STARTING_PAYMENT:
				row.amount_need_to_pay = get_month_amount(student, month)
			else:
				row.amount_need_to_pay = flt(detail.amount_need_to_pay) or get_month_amount(student, month)

			row.pending = max(0.0, flt(row.amount_need_to_pay) - flt(row.amount_paid))
			row.status = get_row_status(row)

			if month == STARTING_PAYMENT:
				self.apply_starting_payment_advance(student, row)

		self.apply_coupon_usage(student, is_submit=is_submit)
		update_student_totals(student)
		student.save(ignore_permissions=True)

	def apply_coupon_usage(self, student, is_submit=True):
		"""Stamp the coupons this invoice redeemed as used, or release them again
		when it is cancelled."""
		codes = get_coupon_codes(self)
		if not codes:
			return

		for row in student.get("coupon_code_details", []):
			if row.referral_coupon_code not in codes:
				continue

			row.used = 1 if is_submit else 0
			row.used_date = frappe.utils.today() if is_submit else None

	def apply_starting_payment_advance(self, student, starting_row):
		"""Settle the months the starting payment pays for in advance.

		A fully paid starting payment settles both the first full month and the
		last month of the academic year; half of it settles the first month
		only. The months are marked Paid without any amount of their own -- the
		money sits against the starting payment row, so counting it again here
		would double it in the student's totals.
		"""
		starting_fee = flt(starting_row.amount_need_to_pay)
		if starting_fee <= 0:
			return

		paid_percentage = (flt(starting_row.amount_paid) / starting_fee) * 100

		first_month, last_month = get_advance_months(student)
		monthly_fee = flt(student.monthly_fee or 0)

		def settle(month, covered):
			if not month:
				return
			row = get_payment_row(student, month)
			if not row:
				row = student.append("payment_details", {"month": month, "amount_paid": 0.0})

			if covered:
				row.amount_need_to_pay = flt(row.amount_need_to_pay) or monthly_fee
				row.pending = 0
				row.status = "Paid"
			elif flt(row.amount_paid) == 0:
				# The advance no longer reaches this month and nothing was paid
				# against it directly, so it goes back to being due.
				row.amount_need_to_pay = flt(row.amount_need_to_pay) or monthly_fee
				row.pending = flt(row.amount_need_to_pay)
				row.status = "Not Paid"

		settle(first_month, paid_percentage >= 50)
		settle(last_month, paid_percentage >= 100)

	def send_receipt_sms(self):
		if float(self.paid_amount or 0) > 0:
			# Mocking a payment_doc since send_payment_confirmation expects one
			class MockPaymentEntry:
				def __init__(self, invoice):
					self.student = invoice.student
					self.amount = invoice.paid_amount
					self.payment_mode = "Cash"
					self.fee_invoice = invoice.name
					self.reference_number = "N/A"

			from bb_tution_management.bb_academy.sms import send_payment_confirmation
			send_payment_confirmation(MockPaymentEntry(self))


def get_row_status(row):
	if flt(row.pending) <= 0:
		return "Paid"
	if flt(row.amount_paid) > 0:
		return "Partial"
	return "Not Paid"


def update_student_totals(student):
	"""Roll the payment_details rows up into the student's paid / pending totals.

	Pending covers the whole academic year, including months that have not been
	invoiced yet, so it reads as what the student still owes overall.
	"""
	total_paid = 0.0
	total_pending = 0.0

	for row in student.get("payment_details", []):
		if row.status == "Not Joined":
			continue

		total_paid += flt(row.amount_paid)

		if row.status == "Paid":
			continue

		billable = flt(row.amount_need_to_pay) or get_month_amount(student, row.month)
		total_pending += max(0.0, billable - flt(row.amount_paid))

	student.total_paid_amount = total_paid
	student.total_pending_amount = total_pending
