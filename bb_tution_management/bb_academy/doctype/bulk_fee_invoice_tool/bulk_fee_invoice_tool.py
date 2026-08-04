# Copyright (c) 2026, Maha Raja and contributors
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
		fields=["name", "student_name", "standard", "current_batch", "monthly_fee", "admission_date", "fees_due_date"]
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
			if ad_date_str:
				ad_date = getdate(ad_date_str)
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
		waived = False
		if fee_month == ay_end_month and starting_balance <= 0:
			waived = True
		
		if not waived:
			items.append({"description": f"{fee_month} Monthly Fee", "amount": flt(student.monthly_fee)})
			
		if not items:
			# Nothing to charge?
			continue

		due_date_val = add_days(today(), 10)
		if student.fees_due_date:
			current_date = getdate(today())
			try:
				due_date_val = current_date.replace(day=student.fees_due_date)
			except ValueError:
				pass

		invoice = frappe.get_doc({
			"doctype": "Fee Invoice",
			"student": student.name,
			"fee_month": fee_month,
			"invoice_date": today(),
			"due_date": due_date_val,
			"is_starting_fee": 0,
			"items": items
		})
		invoice.insert(ignore_permissions=True)
		invoice.submit()
		created_count += 1

	frappe.db.commit()
	return created_count
