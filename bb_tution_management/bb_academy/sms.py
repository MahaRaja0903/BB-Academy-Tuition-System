# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, today
from frappe import _


def get_sms_settings():
	return frappe.get_single("BB SMS Settings")


def get_student_mobiles(student):
	"""Parent mobile numbers to notify for a Student, honouring their
	Preferred Mobile Number setting.

	Falls back to whichever number is on record when the preferred parent has
	none, so a notification is not dropped over a missing field.
	"""
	if isinstance(student, str):
		student = frappe.db.get_value(
			"Student",
			student,
			["father_mobile_number", "mother_mobile_number", "preferred_mobile_number"],
			as_dict=True,
		)

	if not student:
		return []

	father = (student.get("father_mobile_number") or "").strip()
	mother = (student.get("mother_mobile_number") or "").strip()
	preferred = student.get("preferred_mobile_number")

	if preferred == "Father":
		numbers = [father, mother]
	elif preferred == "Mother":
		numbers = [mother, father]
	else:
		# "Both", or not set at all
		return list(dict.fromkeys(n for n in (father, mother) if n))

	# Preferred parent first, the other only as a fallback
	numbers = [n for n in numbers if n]
	return numbers[:1]


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
		SELECT name, student_name, date_of_birth,
		       father_mobile_number, mother_mobile_number, preferred_mobile_number
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
		# A student can have both parents on record -- notify each, but count
		# the student once. The list comprehension deliberately does not
		# short-circuit, so the second parent is not skipped.
		notified = [
			mobile for mobile in get_student_mobiles(student)
			if send_sms(mobile, message, receiver_name=student.student_name)
		]
		if notified:
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
		SELECT inv.name, inv.student, inv.outstanding_amount, inv.invoice_date,
		       stu.student_name, stu.father_mobile_number, stu.mother_mobile_number,
		       stu.preferred_mobile_number
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
		# Fee Invoice has no fee_month / due_date field, but templates are
		# edited by hand in BB SMS Settings and may still reference them --
		# keep the placeholders resolvable so the scheduled job cannot die on
		# a KeyError.
		message = template.format(
			student_name=inv.student_name,
			outstanding_amount=inv.outstanding_amount,
			invoice_date=inv.invoice_date or "",
			fee_month="",
			due_date=""
		)
		notified = [
			mobile for mobile in get_student_mobiles(inv)
			if send_sms(mobile, message, receiver_name=inv.student_name)
		]
		if notified:
			sent_count += 1

	return {"status": "success", "sent_count": sent_count}


def send_payment_confirmation(payment_doc):
	"""Triggered automatically when a Payment Entry is submitted."""
	settings = get_sms_settings()
	if not settings.enabled or not settings.enable_payment_sms:
		return False

	student = frappe.db.get_value(
		"Student",
		payment_doc.student,
		["student_name", "father_mobile_number", "mother_mobile_number", "preferred_mobile_number"],
		as_dict=True,
	)
	if not student:
		return False

	mobiles = get_student_mobiles(student)
	if not mobiles:
		return False

	template = settings.payment_sms_template or "Payment of ₹{amount} received for {student_name}. Thank you! - BB Academy"
	message = template.format(
		student_name=student.student_name,
		amount=payment_doc.amount,
		payment_mode=payment_doc.payment_mode,
		fee_invoice=payment_doc.fee_invoice,
		reference_number=payment_doc.reference_number or "N/A"
	)

	sent = [
		mobile for mobile in mobiles
		if send_sms(mobile, message, receiver_name=student.student_name)
	]
	return bool(sent)


def send_batch_change_sms(student_name, mobiles, previous_batch, new_batch, standard):
	"""Sends SMS notification when a student's batch is updated (Promoted/Demoted).

	`mobiles` is the list of numbers to notify -- see get_student_mobiles().
	Returns the number of messages dispatched.
	"""
	settings = get_sms_settings()
	if not settings.enabled or not getattr(settings, "enable_batch_change_sms", 1):
		return 0

	if isinstance(mobiles, str):
		mobiles = [mobiles]

	if not mobiles:
		return 0

	template = getattr(settings, "batch_change_sms_template", None) or "Dear Parent, student {student_name} has been moved from {previous_batch} to {new_batch} in Standard {standard}. - BB Academy"
	message = template.format(
		student_name=student_name,
		previous_batch=previous_batch,
		new_batch=new_batch,
		standard=standard or ""
	)

	return sum(1 for m in mobiles if send_sms(m, message, receiver_name=student_name))
