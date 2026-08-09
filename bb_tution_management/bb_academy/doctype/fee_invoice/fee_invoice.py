# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

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
			"amount_paid": float(row.amount_paid or 0),
			"pending": float(row.pending or 0),
		})

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
	}


class FeeInvoice(Document):
	def validate(self):
		self.validate_duplicate_invoice()
		self.calculate_outstanding()
		# self.update_status()

	def validate_duplicate_invoice(self):
		is_starting = getattr(self, "is_starting_fee", 0)
		if self.student and not is_starting:
			for detail in self.get("fees_details", []):
				month = detail.month
				if not month or month == "Starting Payment":
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
		if self.student:
			student_doc = frappe.get_doc("Student", self.student)
			total_fee = 0.0
			total_paid = 0.0
			
			if self.get("fees_details"):
				for row in self.fees_details:
					if row.month == "Starting Payment":
						total_fee += float(student_doc.starting_payment or 0)
					elif row.month:
						total_fee += float(student_doc.monthly_fee or 0)
					total_paid += float(row.paid_amount or 0)
						
				self.monthly_fee = total_fee
				if total_paid > 0 or len(self.fees_details) > 0:
					self.paid_amount = total_paid

		discount = float(self.discount_amount or 0) if self.add_discount else 0.0
		net_total = float(self.monthly_fee or 0) - discount
		
		if self.apply_gst_18:
			self.gst_amount = net_total * 0.18
		else:
			self.gst_amount = 0.0
			
		self.grand_total = net_total + self.gst_amount
		outstanding_amount = float(self.outstanding_amount or 0)
		final_total = self.grand_total + outstanding_amount
		paid_amount = float(self.paid_amount or 0)
		self.balance_amount = max(0.0, final_total - paid_amount)

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

		for detail in self.get("fees_details", []):
			month = detail.month
			if not month:
				continue

			existing_row = None
			for row in student.get("payment_details", []):
				if row.month == month:
					existing_row = row
					break

			if not existing_row:
				existing_row = student.append("payment_details", {
					"month": month,
					"amount_paid": 0.0
				})

			detail_paid = float(detail.paid_amount or 0)
			if detail_paid == 0 and len(self.get("fees_details", [])) == 1:
				detail_paid = float(self.paid_amount or 0)

			if is_submit:
				existing_row.amount_paid = float(existing_row.amount_paid or 0) + detail_paid
			else:
				existing_row.amount_paid = max(0.0, float(existing_row.amount_paid or 0) - detail_paid)

			existing_row.date = frappe.utils.today()
			
			if month == "Starting Payment":
				total_fee = float(student.starting_payment or 0)
			else:
				total_fee = float(student.monthly_fee or 0)
				
			existing_row.pending = max(0.0, total_fee - float(existing_row.amount_paid or 0))

			if existing_row.pending <= 0:
				existing_row.status = "Paid"
			elif existing_row.amount_paid > 0:
				existing_row.status = "Partial"
			else:
				existing_row.status = "Not Paid"

			# Handling Starting Payment Concessions
			if month == "Starting Payment":
				starting_fee = float(student.starting_payment or 0)
				if starting_fee > 0:
					paid_percentage = (float(existing_row.amount_paid or 0) / starting_fee) * 100
					
					# Find academic months in payment_details
					academic_rows = [row for row in student.get("payment_details", []) if row.month != "Starting Payment" and row.status != "Not Joined"]
					
					if academic_rows:
						ad_date = frappe.utils.getdate(student.admission_date) if student.admission_date else frappe.utils.getdate()
						first_month_index = 0
						if ad_date.day > 10 and len(academic_rows) > 1:
							first_month_index = 1
							
						first_month_row = academic_rows[first_month_index]
						last_month_row = academic_rows[-1]
						monthly_fee = float(student.monthly_fee or 0)
						
						if paid_percentage >= 100:
							first_month_row.status = "Paid"
							first_month_row.pending = 0
							last_month_row.status = "Paid"
							last_month_row.pending = 0
						elif paid_percentage >= 50:
							first_month_row.status = "Paid"
							first_month_row.pending = 0
							
							if float(last_month_row.amount_paid or 0) == 0:
								last_month_row.status = "Not Paid"
								last_month_row.pending = monthly_fee
						else:
							if float(first_month_row.amount_paid or 0) == 0:
								first_month_row.status = "Not Paid"
								first_month_row.pending = monthly_fee
							if float(last_month_row.amount_paid or 0) == 0:
								last_month_row.status = "Not Paid"
								last_month_row.pending = monthly_fee

		student.save(ignore_permissions=True)

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
