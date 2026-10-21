# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

"""Monthly WhatsApp fee reminder, sent at 12:00 PM the day after each student's due day.

Runs daily from hooks.py; a student whose fees_due_date is 5 is messaged on the
6th of every month, only while that month's fee is still unpaid. Goes out
through the approved fee_reminder-en template:
{{1}} மகன் / மகள், {{2}} student name, {{3}} student ID, {{4}} STD, {{5}} batch,
{{6}} fee amount, {{7}} due date.
"""

import json
from calendar import monthrange

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, today

from bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice import (
	MONTH_NAMES,
	SETTLED_STATUSES,
	get_payment_row,
	get_row_default_amount,
)
from bb_tution_management.bb_academy.missing_details import get_whatsapp_account

TEMPLATE = "fee_reminder-en"

# {{1}} -- whose fee it is, from the student's gender.
RELATION = {"Boys": "மகன்", "Girls": "மகள்"}


def get_due_day(fees_due_date, on_date):
	"""The day of on_date's month the fee falls due; a 30/31 due day falls on
	the month's last day in shorter months."""
	return min(cint(fees_due_date), monthrange(on_date.year, on_date.month)[1])


def get_recipients(due_date):
	"""Active monthly-fee students whose due day is due_date."""
	students = frappe.get_all(
		"Student",
		filters={
			"status": "Active",
			"fees_due_date": [">", 0],
			"yearly_fees_student": 0,
			"scholarship_student": 0,
		},
		fields=["name", "fees_due_date"],
		order_by="name asc",
	)
	return [s.name for s in students if get_due_day(s.fees_due_date, due_date) == due_date.day]


def already_sent(student, on_date):
	"""Guards a rerun on the same day; each due date gets one reminder."""
	return frappe.db.exists(
		"WhatsApp Message",
		{
			"template": TEMPLATE,
			"reference_doctype": "Student",
			"reference_name": student,
			"status": ["!=", "Failed"],
			"creation": [">=", on_date],
		},
	)


def build_body_params(student_doc, amount, due_date):
	# Values in template order: {{1}} .. {{7}}
	return {
		"1": RELATION.get(student_doc.gender, "மகன்/மகள்"),
		"2": (student_doc.student_name or "").strip(),
		"3": student_doc.name,
		"4": student_doc.standard or "",
		"5": student_doc.current_batch or "",
		"6": str(amount),
		"7": due_date.strftime("%d/%m/%Y"),
	}


def send_fee_reminders(on_date=None):
	"""Message every student whose fee fell due the day before on_date (default
	today) and whose month is still unpaid."""
	on_date = getdate(on_date or today())
	due_date = add_days(on_date, -1)
	month = MONTH_NAMES[due_date.month - 1]
	whatsapp_account = get_whatsapp_account()
	sent, failed, skipped = 0, [], []

	for name in get_recipients(due_date):
		student_doc = frappe.get_doc("Student", name)

		row = get_payment_row(student_doc, month)
		# No row means the month is outside the student's academic year.
		if not row or row.status in SETTLED_STATUSES or row.status == "No Fees":
			continue

		amount = get_row_default_amount(student_doc, month)
		if amount <= 0 or already_sent(name, on_date):
			continue

		if not student_doc.preferred_whatsapp_number:
			skipped.append(name)
			continue

		try:
			frappe.get_doc({
				"doctype": "WhatsApp Message",
				"type": "Outgoing",
				"message_type": "Template",
				"content_type": "text",
				"whatsapp_account": whatsapp_account,
				"to": student_doc.preferred_whatsapp_number,
				"template": TEMPLATE,
				"reference_doctype": "Student",
				"reference_name": name,
				"body_param": json.dumps(build_body_params(student_doc, amount, due_date), ensure_ascii=False),
			}).insert(ignore_permissions=True)
			frappe.db.commit()
			sent += 1
		except Exception:
			frappe.db.rollback()
			failed.append(name)
			frappe.log_error(frappe.get_traceback(), "Fee reminder WhatsApp failed: {0}".format(name))

	if failed or skipped:
		frappe.log_error(
			_("Fee reminder {0}: {1} sent. Failed: {2}. No WhatsApp number: {3}").format(
				on_date, sent, ", ".join(failed) or "-", ", ".join(skipped) or "-"
			),
			"Fee reminder WhatsApp",
		)

	return {"sent": sent, "failed": failed, "no_number": skipped}


def send_scheduled():
	"""Daily 12:00 PM run (hooks.py)."""
	if not frappe.db.exists("WhatsApp Templates", TEMPLATE):
		frappe.log_error(_("WhatsApp template {0} is missing.").format(TEMPLATE), "Fee reminder WhatsApp")
		return

	# A cron job gets the short default queue timeout; many sends need the long queue.
	frappe.enqueue(
		send_fee_reminders,
		queue="long",
		timeout=3600,
		on_date=today(),
		job_id="send_fee_reminders",
		deduplicate=True,
	)
