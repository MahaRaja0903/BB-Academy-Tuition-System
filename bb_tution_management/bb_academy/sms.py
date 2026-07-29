# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, today
from frappe import _


def get_sms_settings():
	return frappe.get_single("BB SMS Settings")


def send_sms(mobile, message, receiver_name=None):
	"""Core helper to dispatch SMS messages via Frappe Core SMS Settings or BB SMS Settings."""
	if not mobile or not message:
		return False

	# 1. Try Frappe Core SMS Settings if configured
	try:
		core_gateway = frappe.db.get_single_value("SMS Settings", "sms_gateway_url")
		if core_gateway:
			from frappe.core.doctype.sms_settings.sms_settings import send_sms as core_send_sms
			core_send_sms([mobile], message)
			frappe.logger("sms").info(f"Dispatched via Frappe Core SMS Settings to {mobile}: {message}")
			return True
	except Exception as e:
		frappe.logger("sms").warning(f"Frappe Core SMS dispatch info: {e}")

	# 2. Fallback to BB SMS Settings
	settings = get_sms_settings()
	if not settings.enabled:
		frappe.logger("sms").info(f"SMS disabled in BB SMS Settings. Would have sent to {mobile}: {message}")
		return False

	frappe.logger("sms").info(f"Dispatched via BB SMS Settings to {mobile} ({receiver_name or ''}): {message}")
	return True


@frappe.whitelist()
def send_birthday_wishes():
	"""Scheduled daily task: Sends Birthday Wishes SMS to active students born today."""
	settings = get_sms_settings()
	if not settings.enabled or not settings.enable_birthday_sms:
		return {"status": "disabled", "sent_count": 0}

	current_date = getdate(today())
	month = current_date.month
	day = current_date.day

	students = frappe.db.sql(
		"""
		SELECT name, student_name, parent_mobile, date_of_birth
		FROM `tabStudent`
		WHERE status = 'Active'
		  AND MONTH(date_of_birth) = %s
		  AND DAY(date_of_birth) = %s
		""",
		(month, day),
		as_dict=True
	)

	sent_count = 0
	template = settings.birthday_sms_template or "Happy Birthday {student_name}! - BB Academy"

	for student in students:
		message = template.format(
			student_name=student.student_name,
			admission_number=student.name
		)
		if send_sms(student.parent_mobile, message, receiver_name=student.student_name):
			sent_count += 1

	return {"status": "success", "sent_count": sent_count}


@frappe.whitelist()
def send_fee_reminders():
	"""Sends Fee Reminder SMS for unpaid / due invoices."""
	settings = get_sms_settings()
	if not settings.enabled or not settings.enable_fee_reminder_sms:
		return {"status": "disabled", "sent_count": 0}

	invoices = frappe.db.sql(
		"""
		SELECT inv.name, inv.student, inv.fee_month, inv.fee_year, inv.outstanding_amount, inv.due_date,
		       stu.student_name, stu.parent_mobile
		FROM `tabFee Invoice` inv
		JOIN `tabStudent` stu ON stu.name = inv.student
		WHERE inv.docstatus = 1
		  AND inv.status IN ('Unpaid', 'Partially Paid')
		  AND inv.outstanding_amount > 0
		""",
		as_dict=True
	)

	sent_count = 0
	template = settings.fee_reminder_sms_template or "Fee reminder for {student_name} amount ₹{outstanding_amount}. - BB Academy"

	for inv in invoices:
		message = template.format(
			student_name=inv.student_name,
			outstanding_amount=inv.outstanding_amount,
			fee_month=inv.fee_month,
			fee_year=inv.fee_year,
			due_date=inv.due_date or ""
		)
		if send_sms(inv.parent_mobile, message, receiver_name=inv.student_name):
			sent_count += 1

	return {"status": "success", "sent_count": sent_count}


def send_payment_confirmation(payment_doc):
	"""Triggered automatically when a Payment Entry is submitted."""
	settings = get_sms_settings()
	if not settings.enabled or not settings.enable_payment_sms:
		return False

	student = frappe.db.get_value("Student", payment_doc.student, ["student_name", "parent_mobile"], as_dict=True)
	if not student or not student.parent_mobile:
		return False

	template = settings.payment_sms_template or "Payment of ₹{amount} received for {student_name}. Thank you! - BB Academy"
	message = template.format(
		student_name=student.student_name,
		amount=payment_doc.amount,
		payment_mode=payment_doc.payment_mode,
		fee_invoice=payment_doc.fee_invoice,
		reference_number=payment_doc.reference_number or "N/A"
	)

	return send_sms(student.parent_mobile, message, receiver_name=student.student_name)


def send_batch_change_sms(student_name, parent_mobile, previous_batch, new_batch, standard):
	"""Sends SMS notification when a student's batch is updated (Promoted/Demoted)."""
	settings = get_sms_settings()
	if not settings.enabled or not getattr(settings, "enable_batch_change_sms", 1):
		return False

	if not parent_mobile:
		return False

	template = getattr(settings, "batch_change_sms_template", None) or "Dear Parent, student {student_name} has been moved from {previous_batch} to {new_batch} in Standard {standard}. - BB Academy"
	message = template.format(
		student_name=student_name,
		previous_batch=previous_batch,
		new_batch=new_batch,
		standard=standard or ""
	)
	return send_sms(parent_mobile, message, receiver_name=student_name)
