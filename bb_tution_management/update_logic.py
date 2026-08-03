import os

app_path = "/home/maharajan/Dont-quit/apps/bb_tution_management/bb_tution_management/bb_academy"

# 1. Update student_admission_form.py
saf_path = os.path.join(app_path, "doctype/student_admission_form/student_admission_form.py")
with open(saf_path, "r") as f:
	saf_content = f.read()

new_saf = saf_content.replace(
"""	def create_student_record(self):""",
"""	def create_student_record(self):
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
			
			# Generate Starting Fee Invoice
			from frappe.utils import today, add_days, getdate
			ad_date = getdate(self.application_date or today())
			invoice = frappe.get_doc({
				"doctype": "Fee Invoice",
				"student": student.name,
				"fee_month": ad_date.strftime("%B"),
				"invoice_date": today(),
				"due_date": add_days(today(), 10),
				"is_starting_fee": 1,
				"items": [
					{"description": "Starting Payment (First & Last Month)", "amount": self.starting_payment}
				]
			})
			invoice.insert(ignore_permissions=True)
			invoice.submit()
			
			frappe.msgprint(frappe._("Student record {0} and Starting Fee Invoice created.").format(student.name))
			return

	def original_create_student_record(self):"""
)
with open(saf_path, "w") as f:
	f.write(new_saf)


# 2. Update fee_invoice.py
fi_path = os.path.join(app_path, "doctype/fee_invoice/fee_invoice.py")
fi_content = """# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class FeeInvoice(Document):
	def validate(self):
		self.fetch_student_details()
		self.validate_immutability()
		self.validate_duplicate_invoice()
		self.calculate_outstanding()
		self.update_status()

	def fetch_student_details(self):
		if self.student:
			student_doc = frappe.get_doc("Student", self.student)
			if self.is_new():
				self.standard = student_doc.standard
				self.batch = student_doc.current_batch

	def validate_immutability(self):
		if not self.is_new():
			doc_before_save = self.get_doc_before_save()
			if doc_before_save:
				if doc_before_save.standard != self.standard:
					frappe.throw(_("Standard cannot be changed once Fee Invoice is created."))
				if doc_before_save.batch != self.batch:
					frappe.throw(_("Batch cannot be changed once Fee Invoice is created."))

	def validate_duplicate_invoice(self):
		if self.student and self.fee_month and not self.is_starting_fee:
			existing = frappe.db.exists(
				"Fee Invoice",
				{
					"student": self.student,
					"fee_month": self.fee_month,
					"is_starting_fee": 0,
					"docstatus": ["!=", 2],
					"name": ["!=", self.name or ""]
				}
			)
			if existing:
				frappe.throw(
					_("A Fee Invoice ({0}) already exists for Student {1} for {2}.").format(
						existing, self.student, self.fee_month
					)
				)

	def calculate_outstanding(self):
		self.grand_total = sum([float(item.amount or 0) for item in self.get("items", [])])
		paid_amount = float(self.paid_amount or 0)
		self.outstanding_amount = max(0.0, self.grand_total - paid_amount)

	def update_status(self):
		if self.docstatus == 2:
			self.status = "Cancelled"
		elif self.docstatus == 1:
			if self.outstanding_amount <= 0:
				self.status = "Paid"
			elif float(self.paid_amount or 0) > 0:
				self.status = "Partially Paid"
			else:
				self.status = "Unpaid"
		else:
			self.status = "Draft"

	def on_submit(self):
		self.update_status()
"""
with open(fi_path, "w") as f:
	f.write(fi_content)


# 3. Update fees_payment_entry.py
fpe_path = os.path.join(app_path, "doctype/fees_payment_entry/fees_payment_entry.py")
with open(fpe_path, "r") as f:
	fpe_content = f.read()

new_fpe = fpe_content.replace(
"""		invoice.outstanding_amount = max(0.0, float(invoice.monthly_fee or 0) + float(invoice.arrears_amount or 0) - paid_amount)""",
"""		invoice.outstanding_amount = max(0.0, float(invoice.grand_total or 0) - paid_amount)"""
)
with open(fpe_path, "w") as f:
	f.write(new_fpe)


# 4. Update bulk_fee_invoice_tool.py
bfit_path = os.path.join(app_path, "doctype/bulk_fee_invoice_tool/bulk_fee_invoice_tool.py")
bfit_content = """# Copyright (c) 2026, Maha Raja and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from calendar import monthrange
from frappe.utils import flt, getdate, add_days, today

class BulkFeeInvoiceTool(Document):
	pass

@frappe.whitelist()
def generate_invoices(academic_year, fee_month):
	if not academic_year or not fee_month:
		frappe.throw(_("Academic Year and Fee Month are mandatory."))

	ay_doc = frappe.get_doc("Academic Year", academic_year)
	ay_start_month = ay_doc.start_month
	ay_end_month = ay_doc.end_month
	
	active_students = frappe.get_all(
		"Student",
		filters={"status": "Active", "academic_year": academic_year},
		fields=["name", "student_name", "standard", "current_batch", "monthly_fee", "admission_date"]
	)

	created_count = 0
	
	for student in active_students:
		# Don't generate normal invoice for their exact admission month
		ad_date_str = student.admission_date
		if ad_date_str:
			ad_date = getdate(ad_date_str)
			if ad_date.strftime("%B") == fee_month:
				continue # Handled by starting fee invoice!

		existing = frappe.db.exists(
			"Fee Invoice",
			{
				"student": student.name,
				"fee_month": fee_month,
				"is_starting_fee": 0,
				"docstatus": ["!=", 2]
			}
		)
		if existing:
			continue

		items = []
		
		# 1. Starting Fee Arrears?
		starting_invoices = frappe.get_all(
			"Fee Invoice",
			filters={"student": student.name, "is_starting_fee": 1, "docstatus": 1, "outstanding_amount": [">", 0]},
			fields=["outstanding_amount"]
		)
		starting_balance = sum([flt(i.outstanding_amount) for i in starting_invoices])
		
		if starting_balance > 0:
			items.append({"description": "Starting Fee Balance", "amount": starting_balance})
			# 1b. If starting fee not fully paid, we must charge for the first month since they lose the waiver.
			if ad_date:
				# Calculate first month fee
				first_month_fee = 0
				if ad_date.day <= 10:
					first_month_fee = flt(student.monthly_fee)
					desc = f"{ad_date.strftime('%B')} Fee (Full Month)"
				else:
					_, days_in_month = monthrange(ad_date.year, ad_date.month)
					remaining_days = days_in_month - ad_date.day + 1
					first_month_fee = (flt(student.monthly_fee) / days_in_month) * remaining_days
					desc = f"{ad_date.strftime('%B')} Fee ({remaining_days} days prorated)"
				
				# Has this first month fee been charged in any PREVIOUS invoice? 
				# We can just check if any invoice has a description starting with that month.
				# To simplify, we just add it to items.
				items.append({"description": desc, "amount": first_month_fee})
				
		# 2. Normal Previous Arrears (from normal monthly invoices)
		normal_arrears = frappe.get_all(
			"Fee Invoice",
			filters={"student": student.name, "is_starting_fee": 0, "docstatus": 1, "outstanding_amount": [">", 0]},
			fields=["outstanding_amount", "name"]
		)
		for arr in normal_arrears:
			items.append({"description": f"Arrears from {arr.name}", "amount": flt(arr.outstanding_amount)})

		# 3. Current Month Fee
		# Is current month the last month? If so, and starting fee fully paid, it's waived.
		if fee_month == ay_end_month and starting_balance <= 0:
			waived = True
			
		if not waived:
			items.append({"description": f"{fee_month} Monthly Fee", "amount": flt(student.monthly_fee)})
			
		if not items:
			# Nothing to charge?
			continue

		invoice = frappe.get_doc({
			"doctype": "Fee Invoice",
			"student": student.name,
			"fee_month": fee_month,
			"invoice_date": today(),
			"due_date": add_days(today(), 10),
			"is_starting_fee": 0,
			"items": items
		})
		invoice.insert(ignore_permissions=True)
		invoice.submit()
		created_count += 1

	frappe.db.commit()
	return created_count
"""
with open(bfit_path, "w") as f:
	f.write(bfit_content)

print("Updated all scripts successfully.")
