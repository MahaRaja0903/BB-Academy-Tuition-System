# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

"""Bulk WhatsApp asking active students' parents to fill the student_details form.

Each message carries that student's own link, /student_details?student_id=<id>,
through the approved missing_details_message-en template:
{{1}} student name, {{2}} update form link, {{3}} submit-by date.
"""

import json
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint, formatdate, getdate

TEMPLATE = "missing_details_message-en"
DETAILS_PAGE = "/student_details"

# What the student_details form asks for; blank means the parent hasn't filled it.
DETAIL_FIELDS = ("father_occupation", "mother_occupation")


def get_recipients(only_missing=1, skip_already_sent=1):
	"""Active students to message, with the number to send to."""
	students = frappe.get_all(
		"Student",
		filters={"status": "Active"},
		fields=["name", "student_name", "preferred_whatsapp_number", *DETAIL_FIELDS],
		order_by="name asc",
	)

	if cint(only_missing):
		students = [s for s in students if any(not (s.get(f) or "").strip() for f in DETAIL_FIELDS)]

	if cint(skip_already_sent):
		sent = set(frappe.get_all(
			"WhatsApp Message",
			filters={"template": TEMPLATE, "reference_doctype": "Student", "status": ["!=", "Failed"]},
			pluck="reference_name",
		))
		students = [s for s in students if s.name not in sent]

	return students


def get_whatsapp_account():
	"""The default outgoing account, else the one active account on the site."""
	account = frappe.db.get_value("WhatsApp Account", {"is_default_outgoing": 1, "status": "Active"})
	if account:
		return account

	active = frappe.get_all("WhatsApp Account", filters={"status": "Active"}, pluck="name")
	if len(active) == 1:
		return active[0]

	frappe.throw(_("Mark one WhatsApp Account as Default Outgoing to send this message."))


@frappe.whitelist()
def get_missing_details_summary(only_missing=1, skip_already_sent=1):
	"""Counts for the confirm dialog before anything is sent."""
	frappe.only_for(("System Manager", "Administrator", "Receptionist"))

	students = get_recipients(only_missing, skip_already_sent)
	no_number = [s for s in students if not s.preferred_whatsapp_number]
	return {
		"to_send": len(students) - len(no_number),
		"no_number": [{"name": s.name, "student_name": s.student_name} for s in no_number],
	}


@frappe.whitelist()
def send_missing_details_message(submit_by, only_missing=1, skip_already_sent=1):
	"""Queue the bulk send; the parent gets one message per student."""
	frappe.only_for(("System Manager", "Administrator", "Receptionist"))

	if not frappe.db.exists("WhatsApp Templates", TEMPLATE):
		frappe.throw(_("WhatsApp template {0} is missing.").format(TEMPLATE))
	if getdate(submit_by) < getdate():
		frappe.throw(_("The submit-by date can't be in the past."))
	whatsapp_account = get_whatsapp_account()

	frappe.enqueue(
		send_to_all,
		queue="long",
		timeout=3600,
		# The job has no request, so get_url() there would drop the domain's
		# real scheme/port -- take it from this request instead.
		base_url=frappe.utils.get_url(),
		submit_by=str(getdate(submit_by)),
		whatsapp_account=whatsapp_account,
		only_missing=cint(only_missing),
		skip_already_sent=cint(skip_already_sent),
		user=frappe.session.user,
		job_id="send_missing_details_message",
		deduplicate=True,
	)
	return _("Sending has started in the background. You will be notified when it finishes.")


def send_to_all(base_url, submit_by, whatsapp_account, only_missing, skip_already_sent, user):
	sent, failed, skipped = 0, [], []

	for student in get_recipients(only_missing, skip_already_sent):
		if not student.preferred_whatsapp_number:
			skipped.append(student.name)
			continue

		try:
			frappe.get_doc({
				"doctype": "WhatsApp Message",
				"type": "Outgoing",
				"message_type": "Template",
				"content_type": "text",
				"whatsapp_account": whatsapp_account,
				"to": student.preferred_whatsapp_number,
				"template": TEMPLATE,
				"reference_doctype": "Student",
				"reference_name": student.name,
				# Values in template order: {{1}}, {{2}}, {{3}}
				"body_param": json.dumps({
					"1": (student.student_name or "").strip(),
					"2": "{0}{1}?student_id={2}".format(base_url, DETAILS_PAGE, quote(student.name)),
					"3": formatdate(submit_by, "dd-MM-yyyy"),
				}),
			}).insert(ignore_permissions=True)
			frappe.db.commit()
			sent += 1
		except Exception:
			frappe.db.rollback()
			failed.append(student.name)
			frappe.log_error(
				frappe.get_traceback(), "Missing details WhatsApp failed: {0}".format(student.name)
			)

	summary = _("Missing details WhatsApp: {0} sent, {1} failed, {2} without a number.").format(
		sent, len(failed), len(skipped)
	)
	if failed:
		summary += " " + _("Failed: {0}").format(", ".join(failed))
	if skipped:
		summary += " " + _("No number: {0}").format(", ".join(skipped))

	frappe.publish_realtime("msgprint", {"message": summary, "title": _("WhatsApp")}, user=user)


# Days the parent gets to update the details, counted from the scheduled send.
SUBMIT_WITHIN_DAYS = 7


# The scheduled send is a one-off; cron has no year, so the date guards it.
SEND_ON = "2026-09-23"


def send_scheduled():
	"""One-off 5:30 PM IST run on SEND_ON (hooks.py): active students with
	details still missing who haven't had the message yet."""
	from frappe.utils import add_days, today

	if today() != SEND_ON:
		return

	if not frappe.db.exists("WhatsApp Templates", TEMPLATE):
		frappe.log_error(_("WhatsApp template {0} is missing.").format(TEMPLATE), "Missing details WhatsApp")
		return

	# The scheduler has no request to read the domain from.
	site = frappe.local.site
	base_url = frappe.conf.get("host_name") or "https://{0}".format(site)

	# A cron job gets the short default queue timeout; 150+ sends need the long queue.
	frappe.enqueue(
		send_to_all,
		queue="long",
		timeout=3600,
		base_url=base_url.rstrip("/"),
		submit_by=add_days(today(), SUBMIT_WITHIN_DAYS),
		whatsapp_account=get_whatsapp_account(),
		only_missing=1,
		skip_already_sent=1,
		user="Administrator",
		job_id="send_missing_details_message",
		deduplicate=True,
	)
