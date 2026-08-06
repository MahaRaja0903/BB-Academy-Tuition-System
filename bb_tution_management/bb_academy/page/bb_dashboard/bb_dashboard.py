import frappe
from frappe.utils import nowdate, getdate, add_months, get_first_day, get_last_day, flt


@frappe.whitelist()
def get_dashboard_data():
	"""Single batched call returning all KPI metrics.

	This avoids 6 separate round-trips on page load.
	"""
	today_date = nowdate()
	month_start = get_first_day(today_date)
	month_end = get_last_day(today_date)

	# ── Core counts ─────────────────────────────────────────────────
	active_students = frappe.db.count("Student", {"status": "Active"})
	total_students = frappe.db.count("Student")

	new_admissions = frappe.db.count("Student Admission Form", {
		"docstatus": 1,
		"application_date": ["between", [month_start, month_end]],
	})

	open_enquiries = frappe.db.count("Student Enquiry Form", {
		"status": ["in", ["Open", "Follow-up"]],
	})

	unpaid_invoices = frappe.db.count("Fee Invoice", {
		"docstatus": 1,
		"status": ["in", ["Unpaid", "Partially Paid"]],
	})

	# ── Monetary aggregates ─────────────────────────────────────────
	total_pending = frappe.db.get_value(
		"Fee Invoice",
		{"docstatus": 1, "status": ["in", ["Unpaid", "Partially Paid"]]},
		"sum(outstanding_amount)",
	) or 0

	todays_collections = frappe.db.get_value(
		"Fees Payment Entry",
		{"docstatus": 1, "payment_date": today_date},
		"sum(amount)",
	) or 0

	monthly_collection = frappe.db.get_value(
		"Fees Payment Entry",
		{"docstatus": 1, "payment_date": ["between", [month_start, month_end]]},
		"sum(amount)",
	) or 0

	# Last month for trend comparison
	prev_start = get_first_day(add_months(today_date, -1))
	prev_end = get_last_day(add_months(today_date, -1))
	last_month_collection = frappe.db.get_value(
		"Fees Payment Entry",
		{"docstatus": 1, "payment_date": ["between", [prev_start, prev_end]]},
		"sum(amount)",
	) or 0

	return {
		"active_students": active_students,
		"total_students": total_students,
		"new_admissions": new_admissions,
		"open_enquiries": open_enquiries,
		"unpaid_invoices": unpaid_invoices,
		"total_pending": flt(total_pending, 2),
		"todays_collections": flt(todays_collections, 2),
		"monthly_collection": flt(monthly_collection, 2),
		"last_month_collection": flt(last_month_collection, 2),
	}


@frappe.whitelist()
def get_collection_trend():
	"""Monthly collection totals for the past 12 months."""
	today_date = getdate(nowdate())
	result = []
	for i in range(11, -1, -1):
		d = add_months(today_date, -i)
		ms = get_first_day(d)
		me = get_last_day(d)
		amount = frappe.db.get_value(
			"Fees Payment Entry",
			{"docstatus": 1, "payment_date": ["between", [ms, me]]},
			"sum(amount)",
		) or 0
		result.append({
			"month": getdate(ms).strftime("%b %y"),
			"amount": flt(amount, 2),
		})
	return result


@frappe.whitelist()
def get_invoice_status_breakdown():
	"""Count of submitted invoices grouped by status."""
	return frappe.db.get_all(
		"Fee Invoice",
		filters={"docstatus": 1},
		fields=["status", "count(*) as count"],
		group_by="status",
	)


@frappe.whitelist()
def get_students_by_standard():
	"""Active student count per standard, sorted descending."""
	return frappe.db.get_all(
		"Student",
		filters={"status": "Active"},
		fields=["standard", "count(*) as count"],
		group_by="standard",
		order_by="count desc",
	)


@frappe.whitelist()
def get_enquiry_sources():
	"""Enquiry count grouped by source channel."""
	return frappe.db.get_all(
		"Student Enquiry Form",
		fields=["source", "count(*) as count"],
		group_by="source",
		order_by="count desc",
	)


@frappe.whitelist()
def get_recent_payments():
	"""Last 10 submitted payment entries."""
	return frappe.db.get_all(
		"Fees Payment Entry",
		filters={"docstatus": 1},
		fields=[
			"name", "student", "student_name",
			"amount", "payment_date", "payment_mode",
		],
		order_by="payment_date desc, creation desc",
		limit=10,
	)


@frappe.whitelist()
def get_todays_birthdays():
	"""Active students whose birthday is today (matching month+day)."""
	today = getdate(nowdate())
	students = frappe.db.get_all(
		"Student",
		filters={"status": "Active", "date_of_birth": ["is", "set"]},
		fields=["name", "student_name", "date_of_birth", "standard", "current_batch"],
	)
	return [
		s for s in students
		if getdate(s.date_of_birth).month == today.month
		and getdate(s.date_of_birth).day == today.day
	]


@frappe.whitelist()
def get_pending_followups():
	"""Enquiries with follow-up date today or overdue."""
	return frappe.db.get_all(
		"Student Enquiry Form",
		filters={
			"status": ["in", ["Open", "Follow-up"]],
			"next_follow_up_date": ["<=", nowdate()],
		},
		fields=[
			"name", "applicant_name", "parent_name",
			"parent_mobile", "next_follow_up_date", "standard",
		],
		order_by="next_follow_up_date asc",
		limit=10,
	)


@frappe.whitelist()
def get_overdue_invoices():
	"""Invoices past due date that remain unpaid/partially paid."""
	return frappe.db.get_all(
		"Fee Invoice",
		filters={
			"docstatus": 1,
			"status": ["in", ["Unpaid", "Partially Paid"]],
			"due_date": ["<", nowdate()],
		},
		fields=[
			"name", "student", "student_name",
			"grand_total", "outstanding_amount",
			"due_date", "fee_month",
		],
		order_by="due_date asc",
		limit=10,
	)
