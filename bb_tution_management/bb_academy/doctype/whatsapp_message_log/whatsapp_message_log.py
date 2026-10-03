# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class WhatsAppMessageLog(Document):
	pass


# Where each kind of message is sent from, so a log can't be written against a
# document the user couldn't have sent it from.
MESSAGE_SOURCES = {
	"Fee Bill": "Fee Invoice",
	"Admission Link": "Student Enquiry Form",
}


@frappe.whitelist()
def log_whatsapp_message(
	reference_doctype,
	reference_name,
	message,
	mobile_number,
	message_type="Other",
	recipient_type=None,
	recipient_name=None,
):
	"""Record a WhatsApp message the moment it is handed to WhatsApp.

	Click-to-chat gives no delivery receipt, so this is the send attempt: who it
	was for, the number it went to and the exact text.
	"""
	expected = MESSAGE_SOURCES.get(message_type)
	if expected and expected != reference_doctype:
		frappe.throw(_("{0} messages are sent from {1}.").format(message_type, expected))

	ref = frappe.get_doc(reference_doctype, reference_name)
	ref.check_permission("read")

	student = ref.name if reference_doctype == "Student" else ref.get("student")
	# Admission links go out before there is a Student, so tie those to the enquiry.
	enquiry = ref.name if reference_doctype == "Student Enquiry Form" else None

	log = frappe.get_doc({
		"doctype": "WhatsApp Message Log",
		"student": student,
		"student_name": frappe.db.get_value("Student", student, "student_name") if student
			else ref.get("applicant_name"),
		"student_enquiry": enquiry,
		"message_type": message_type if message_type in ("Fee Bill", "Admission Link") else "Other",
		"sent_on": now_datetime(),
		"sent_by": frappe.session.user,
		"status": "Opened in WhatsApp",
		"recipient_type": recipient_type if recipient_type in ("Father", "Mother", "Guardian") else "Other",
		"recipient_name": recipient_name,
		"mobile_number": mobile_number,
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"message": message,
	}).insert(ignore_permissions=True)

	return log.name


# ---------------------------------------------------------------------------
# Automated messages (frappe_whatsapp)
# ---------------------------------------------------------------------------

# template_name -> Message Type; anything else is logged as "Automated".
TEMPLATE_MESSAGE_TYPES = {
	"student_absent_alert": "Absent Alert",
	"birthday_wishes": "Birthday Wishes",
	"student_joining_message": "Joining Message",
	"missing_details_message": "Missing Details",
}


def sync_from_whatsapp_message(doc, method=None):
	"""doc_events hook on frappe_whatsapp's WhatsApp Message.

	Logs every outgoing message tied to a student and keeps its delivery status
	current as WhatsApp's webhook updates it. Never lets logging break a send.
	"""
	if doc.type != "Outgoing":
		return

	try:
		existing = frappe.db.get_value("WhatsApp Message Log", {"whatsapp_message": doc.name})
		if existing:
			frappe.db.set_value("WhatsApp Message Log", existing, "status", doc.status, update_modified=False)
			return

		student = get_student_for(doc.reference_doctype, doc.reference_name)
		if not student:
			return

		template_name = frappe.db.get_value("WhatsApp Templates", doc.template, "template_name") if doc.template else None
		recipient_type, recipient_name = match_recipient(student, doc.to)

		frappe.get_doc({
			"doctype": "WhatsApp Message Log",
			"student": student,
			"message_type": TEMPLATE_MESSAGE_TYPES.get(template_name, "Automated") if doc.template else "Other",
			"sent_on": doc.creation,
			"sent_by": doc.owner,
			"status": doc.status,
			"recipient_type": recipient_type,
			"recipient_name": recipient_name,
			"mobile_number": doc.to,
			"reference_doctype": doc.reference_doctype,
			"reference_name": doc.reference_name,
			"whatsapp_message": doc.name,
			"template": doc.template,
			"message": render_message(doc),
		}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "WhatsApp Message Log: sync failed")


def get_student_for(reference_doctype, reference_name):
	if not reference_doctype or not reference_name:
		return None
	if reference_doctype == "Student":
		return reference_name if frappe.db.exists("Student", reference_name) else None
	if frappe.get_meta(reference_doctype).has_field("student"):
		return frappe.db.get_value(reference_doctype, reference_name, "student")
	return None


def match_recipient(student, number):
	"""Which parent a number belongs to, compared on the last 10 digits."""
	def tail(value):
		return "".join(ch for ch in (value or "") if ch.isdigit())[-10:]

	target = tail(number)
	info = frappe.db.get_value(
		"Student", student,
		["father_name", "father_mobile_number", "mother_name", "mother_mobile_number",
			"guardian_name", "guardian_mobile_number"],
		as_dict=True,
	) or {}

	for label in ("Father", "Mother", "Guardian"):
		key = label.lower()
		if target and tail(info.get(key + "_mobile_number")) == target:
			return label, info.get(key + "_name")
	return "Other", None


def render_message(doc):
	"""The text the parent actually saw: the template body with its values filled in."""
	if not doc.template:
		return doc.message

	template = frappe.db.get_value(
		"WhatsApp Templates", doc.template, ["header", "template", "footer"], as_dict=True
	)
	if not template or not template.template:
		return doc.message

	try:
		params = json.loads(doc.template_parameters or "[]")
	except ValueError:
		params = []

	body = template.template
	for i, value in enumerate(params, start=1):
		body = body.replace("{{%d}}" % i, str(value))

	return "\n\n".join(part for part in (template.header, body, template.footer) if part)
