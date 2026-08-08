# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate


MONTH_NAMES = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December"
]

# Map month name -> 1-based month number
MONTH_NUMBER = {name: idx + 1 for idx, name in enumerate(MONTH_NAMES)}


class Student(Document):
	def validate(self):
		self.fetch_starting_payment()
		self.fetch_monthly_fee()
		self.populate_payment_details()

	def before_save(self):
		self.track_batch_change()

	# def after_insert(self):
	# 	self.create_starting_fee_invoice()

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

		# ----- fetch academic year start/end months -----
		ay = frappe.get_cached_doc("Academic Year", self.academic_year)
		start_month = MONTH_NUMBER.get(ay.start_month)
		end_month = MONTH_NUMBER.get(ay.end_month)

		if not start_month or not end_month:
			return

		# Build ordered list of month numbers from start_month to end_month
		# e.g. June(6) to March(3) -> [6,7,8,9,10,11,12,1,2,3]
		academic_months = []
		m = start_month
		while True:
			academic_months.append(m)
			if m == end_month:
				break
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
					"amount_paid": starting_payment_row.amount_paid,
					"pending": starting_payment_row.pending,
				})
			else:
				self.append("payment_details", {
					"month": "Starting Payment",
					"status": "Not Paid",
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

	def fetch_starting_payment(self):
		if self.standard:
			starting_payment = frappe.db.get_value("Standard", self.standard, "starting_payment")
			if starting_payment is not None:
				self.starting_payment = starting_payment

	def fetch_monthly_fee(self):
		if self.standard and self.current_batch:
			monthly_fee = frappe.db.get_value(
				"Fee Structure",
				{
					"standard": self.standard,
					"batch": self.current_batch,
					# "is_active": 1,
				},
				"monthly_fee"
			)
			if monthly_fee is not None:
				self.monthly_fee = monthly_fee

	def track_batch_change(self):
		if self.is_new() or getattr(self.flags, "ignore_batch_history", False):
			return

		doc_before_save = self.get_doc_before_save()
		if doc_before_save and doc_before_save.current_batch != self.current_batch:
			previous_batch = doc_before_save.current_batch
			new_batch = self.current_batch

			history_doc = frappe.get_doc({
				"doctype": "Student Batch History",
				"student": self.name,
				"previous_batch": previous_batch,
				"new_batch": new_batch,
				"effective_date": frappe.utils.today(),
				"reason": _("Batch updated for student {0} from {1} to {2}").format(
					self.student_name, previous_batch, new_batch
				),
				"approved_by": frappe.session.user or "Administrator"
			})
			history_doc.flags.ignore_student_update = True
			history_doc.insert(ignore_permissions=True)
			frappe.msgprint(
				_("Student batch change recorded in Student Batch History from {0} to {1}.").format(
					previous_batch, new_batch
				)
			)


