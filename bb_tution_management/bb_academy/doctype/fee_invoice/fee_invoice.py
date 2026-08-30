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

# Payment Method value that means the money came in as more than one form.
SPLIT_UP = "Split Up"

# A month settled out of the starting payment rather than paid for on its own,
# and a month the starting payment has booked but not yet paid for.
PAID_BY_STARTING_PAYMENT = "Paid By Starting Payment"
RESERVED = "Reserved"

# Statuses that mean the month is settled -- nothing left to bill or chase.
SETTLED_STATUSES = ("Paid", PAID_BY_STARTING_PAYMENT, "Not Joined")

# A student who joins on or before this day of the month is billed for the whole
# month; joining later is billed only for the days that are left in the month.
PRORATA_CUTOFF_DAY = 10


def get_academic_months(academic_year):
	"""Month names of an academic year, in calendar order from its start month.

	e.g. an April -> March year gives [April, May, ... February, March], and a
	June -> April one gives [June, July, ... March, April].

	A year that ends in the month it starts in -- April -> April -- runs a full
	cycle, so it gives the twelve distinct months from April round to March. The
	end month is only a stopping point once the year is actually under way; the
	months are keyed by name, so a thirteenth month repeating April is not
	something the payment rows can hold.
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
		if len(months) == 12 or (m == end_month and len(months) > 1):
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
	if row and row.status in SETTLED_STATUSES:
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
		self.validate_discount_amount()
		self.calculate_outstanding()
		self.validate_split_up_payment()
		# self.update_status()

	def validate_split_up_payment(self):
		"""A Split Up payment is the Grand Total handed over in more than one
		form, so Cash + GPAY + Scanner has to add back up to the Grand Total.

		Any other payment method is collected in that one form, so the split
		fields are cleared instead of being left with stale amounts.
		"""
		if self.payment_method != SPLIT_UP:
			self.cash = 0
			self.gpay = 0
			self.scanner = 0
			return

		currency = frappe.db.get_default("currency") or "INR"

		def money(amount):
			return frappe.utils.fmt_money(flt(amount), currency=currency)

		parts = [("Cash", flt(self.cash)), ("GPAY", flt(self.gpay)), ("Scanner", flt(self.scanner))]

		for label, amount in parts:
			if amount < 0:
				frappe.throw(
					_("Split Up: {0} cannot be a negative amount.").format(_(label)),
					title=_("Split Up Payment"),
				)

		collected = sum(amount for _label, amount in parts)
		grand_total = flt(self.grand_total)

		breakup = " + ".join(
			"{0} {1}".format(_(label), money(amount)) for label, amount in parts
		)

		if not collected:
			frappe.throw(
				_("Payment Method is Split Up, so enter how the {0} was collected across Cash, GPAY and Scanner. All three are currently empty.").format(
					money(grand_total)
				),
				title=_("Split Up Payment"),
			)

		difference = flt(collected - grand_total, 2)
		if abs(difference) < 0.01:
			return

		if difference > 0:
			gap = _("That is {0} more than the Grand Total.").format(money(difference))
		else:
			gap = _("That is {0} short of the Grand Total.").format(money(abs(difference)))

		frappe.throw(
			_("Split Up payment does not match the Grand Total.<br><br>Collected: {0} = <b>{1}</b><br>Grand Total: <b>{2}</b><br><br>{3} Change the amount collected in Cash, GPAY or Scanner so the three together come to {2}.").format(
				breakup, money(collected), money(grand_total), gap
			),
			title=_("Split Up Payment"),
		)

	def validate_discount_amount(self):
		if self.add_discount and flt(self.discount_amount) > 0:
			discount_limit = flt(frappe.db.get_single_value("BB Academy Settings", "discount_amount_limit"))
			if flt(self.discount_amount) > discount_limit:
				frappe.throw(_("Discount Amount cannot exceed the limit of {0}").format(discount_limit))

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
		last month of the academic year. Half of it settles the first month and
		only holds the last one: that month is Reserved -- booked against the
		rest of the starting payment, but not paid for yet, so it still shows as
		due.

		A settled month carries Paid By Starting Payment rather than plain Paid,
		so it is clear on the student's record that no money was collected for
		that month on its own -- it sits against the starting payment row, and
		counting it again here would double it in the student's totals.
		"""
		starting_fee = flt(starting_row.amount_need_to_pay)
		if starting_fee <= 0:
			return

		paid_percentage = (flt(starting_row.amount_paid) / starting_fee) * 100

		first_month, last_month = get_advance_months(student)
		monthly_fee = flt(student.monthly_fee or 0)

		def settle(month, status):
			if not month:
				return
			row = get_payment_row(student, month)
			if not row:
				row = student.append("payment_details", {"month": month, "amount_paid": 0.0})

			if status != PAID_BY_STARTING_PAYMENT and flt(row.amount_paid) != 0:
				# Money was paid against this month directly, so what the row
				# already says is the truer reading -- an advance that no longer
				# reaches this month does not overwrite it.
				return

			row.amount_need_to_pay = flt(row.amount_need_to_pay) or monthly_fee

			if status == PAID_BY_STARTING_PAYMENT:
				row.pending = 0
			else:
				# Reserved and Not Paid both still owe the month's fee.
				row.pending = max(0.0, flt(row.amount_need_to_pay) - flt(row.amount_paid))

			row.status = status or "Not Paid"

		settle(
			first_month,
			PAID_BY_STARTING_PAYMENT if paid_percentage >= 50 else None,
		)
		settle(
			last_month,
			PAID_BY_STARTING_PAYMENT if paid_percentage >= 100
			else (RESERVED if paid_percentage >= 50 else None),
		)

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

		# A month settled by the starting payment is already paid for, by the
		# money sitting on the starting payment row.
		if row.status in ("Paid", PAID_BY_STARTING_PAYMENT):
			continue

		billable = flt(row.amount_need_to_pay) or get_month_amount(student, row.month)
		total_pending += max(0.0, billable - flt(row.amount_paid))

	student.total_paid_amount = total_paid
	student.total_pending_amount = total_pending


# ---------------------------------------------------------------------------
# WhatsApp bill
# ---------------------------------------------------------------------------

WHATSAPP_PRINT_FORMAT = "Fee Invoice Modern Print"

# wa.me needs a country code; the numbers on file are plain 10 digit Indian ones.
DEFAULT_COUNTRY_CODE = "91"


def normalize_whatsapp_number(number):
	"""wa.me wants digits only, country code included and no leading +."""
	digits = "".join(ch for ch in (number or "") if ch.isdigit())
	if not digits:
		return ""

	# 0XXXXXXXXXX -> drop the trunk prefix, 00 91 ... -> drop the IDD prefix
	if len(digits) == 11 and digits.startswith("0"):
		digits = digits[1:]
	elif digits.startswith("00"):
		digits = digits[2:]

	if len(digits) == 10:
		digits = DEFAULT_COUNTRY_CODE + digits

	return digits


def get_bill_attachment_url(invoice):
	"""Public URL of this invoice's bill PDF, generating and attaching it once.

	WhatsApp click-to-chat cannot carry a file, so the bill travels as a link in
	the message and has to be readable without logging in.
	"""
	file_name = "{0}.pdf".format(invoice.name.replace("/", "-"))

	existing = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": invoice.doctype,
			"attached_to_name": invoice.name,
			"is_private": 0,
			"file_name": file_name,
		},
		fields=["file_url"],
		order_by="creation desc",
		limit=1,
	)
	if existing:
		return existing[0].file_url

	try:
		pdf = frappe.get_print(
			invoice.doctype,
			invoice.name,
			print_format=WHATSAPP_PRINT_FORMAT,
			as_pdf=True,
		)

		file_doc = frappe.get_doc({
			"doctype": "File",
			"file_name": file_name,
			"attached_to_doctype": invoice.doctype,
			"attached_to_name": invoice.name,
			"is_private": 0,
			"content": pdf,
		}).insert(ignore_permissions=True)
	except Exception:
		# A missing PDF renderer shouldn't stop the parent being told they paid --
		# the message just goes without the link.
		frappe.log_error(
			frappe.get_traceback(), "Fee Invoice: WhatsApp bill PDF failed"
		)
		return ""

	return file_doc.file_url


def build_whatsapp_bill_message(invoice, student, bill_url):
	"""The payment confirmation the parent receives, mirroring the invoice."""
	currency = frappe.db.get_default("currency") or "INR"

	def money(amount):
		return frappe.utils.fmt_money(flt(amount), currency=currency)

	rows = [row for row in invoice.get("fees_details", []) if row.month]
	months = [row.month for row in rows]
	starting_row = next((row for row in rows if row.month == STARTING_PAYMENT), None)

	lines = [
		"*{0}*".format(frappe.db.get_default("company") or "BB Academy"),
		"",
		_("Your payment has been successfully received."),
		"",
		"*{0}*".format(_("Student Details")),
		"{0}: {1}".format(_("Name"), student.student_name or invoice.student),
	]

	if student.admission_number:
		lines.append("{0}: {1}".format(_("Admission No"), student.admission_number))
	if student.standard:
		lines.append("{0}: {1}".format(_("Standard"), student.standard))
	if student.current_batch:
		lines.append("{0}: {1}".format(_("Batch"), student.current_batch))

	lines += [
		"",
		"*{0}*".format(_("Payment Details")),
		"{0}: {1}".format(_("Invoice No"), invoice.name),
		"{0}: {1}".format(
			_("Date"), frappe.utils.formatdate(invoice.invoice_date or nowdate())
		),
	]

	if months:
		lines.append("{0}: {1}".format(_("Month(s) Paid"), ", ".join(months)))
	if starting_row:
		# The starting payment settles the first full month at 50% paid and the
		# last month of the year at 100%; in between the last month is only held.
		# Same rule as apply_starting_payment_advance.
		billed = flt(starting_row.amount_need_to_pay)
		percent = (flt(starting_row.paid_amount) / billed * 100) if billed else 0
		first_month, last_month = get_advance_months(student)

		covered = []
		if percent >= 50 and first_month:
			covered.append(first_month)
		if percent >= 100 and last_month:
			covered.append(last_month)

		if covered:
			lines.append("{0}: {1}".format(
				_("Starting Payment also covers"), ", ".join(covered)
			))
		else:
			lines.append(_("Starting Payment is not settled in full yet."))

		if 50 <= percent < 100 and last_month:
			lines.append("{0}: {1} {2}".format(
				_("Reserved"), last_month,
				_("is held against the rest of the Starting Payment and is still due."),
			))

	lines.append("{0}: {1}".format(_("Total Fees"), money(invoice.monthly_fee)))

	if invoice.add_discount and flt(invoice.discount_amount) > 0:
		lines.append("{0}: -{1}".format(_("Discount"), money(invoice.discount_amount)))

	if invoice.apply_gst_18 and flt(invoice.gst_amount) > 0:
		lines.append("{0}: {1}".format(_("GST 18%"), money(invoice.gst_amount)))

	if flt(invoice.grand_total) != flt(invoice.monthly_fee):
		lines.append("{0}: {1}".format(_("Grand Total"), money(invoice.grand_total)))

	coupons = get_coupon_codes(invoice)
	if coupons and flt(invoice.coupon_amount) > 0:
		lines.append("{0} ({1}): -{2}".format(
			_("Coupon"), ", ".join(coupons), money(invoice.coupon_amount)
		))

	lines.append("*{0}: {1}*".format(_("Amount Paid"), money(invoice.paid_amount)))

	if flt(invoice.balance_amount) > 0:
		lines.append("{0}: {1}".format(_("Balance Due"), money(invoice.balance_amount)))
	else:
		lines.append(_("No balance pending. Thank you!"))

	if bill_url:
		lines += ["", "{0}: {1}".format(_("Bill Invoice"), bill_url)]

	return "\n".join(lines)


@frappe.whitelist()
def get_whatsapp_bill(invoice):
	"""Numbers to send this invoice's bill to, plus the message and bill link."""
	doc = frappe.get_doc("Fee Invoice", invoice)
	doc.check_permission("read")

	student = frappe.get_doc("Student", doc.student)

	contacts = []
	for parent in ("Father", "Mother"):
		fieldname = "{0}_mobile_number".format(parent.lower())
		raw = (student.get(fieldname) or "").strip()
		if not raw:
			continue
		contacts.append({
			"parent": parent,
			"label": _(parent),
			"name": student.get("{0}_name".format(parent.lower())) or "",
			"raw": raw,
			"number": normalize_whatsapp_number(raw),
			"preferred": student.preferred_mobile_number in (parent, "Both"),
		})

	bill_url = get_bill_attachment_url(doc)
	site_url = frappe.utils.get_url()

	return {
		"contacts": contacts,
		"bill_url": site_url + bill_url if bill_url else "",
		"message": build_whatsapp_bill_message(
			doc, student, site_url + bill_url if bill_url else ""
		),
	}
