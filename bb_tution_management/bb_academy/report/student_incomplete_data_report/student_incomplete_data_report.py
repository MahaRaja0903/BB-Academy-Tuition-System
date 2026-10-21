# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

"""Students whose profile is not fully collected: photo or any tracked detail
blank. Students with every tracked field filled are left out."""

import frappe
from frappe import _
from frappe.utils import cint, flt

# Field -> label shown in the "Missing Details" column. Guardian, skills and
# achievement are optional on the forms, so they don't count here.
TRACKED_FIELDS = {
	"image": "Photo",
	"date_of_birth": "Date of Birth",
	"blood_group": "Blood Group",
	"school_name": "School",
	"father_name": "Father Name",
	"father_mobile_number": "Father Mobile",
	"father_occupation": "Father Occupation",
	"mother_name": "Mother Name",
	"mother_mobile_number": "Mother Mobile",
	"mother_occupation": "Mother Occupation",
	"preferred_whatsapp_number": "WhatsApp Number",
	"address": "Address",
	"area": "Area",
	"street_name": "Street Name",
}


def execute(filters=None):
	filters = filters or {}
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"fieldname": "student", "label": _("Student ID"), "fieldtype": "Link", "options": "Student", "width": 150},
		{"fieldname": "student_name", "label": _("Student Name"), "fieldtype": "Data", "width": 200},
		{"fieldname": "standard", "label": _("Standard"), "fieldtype": "Link", "options": "Standard", "width": 120},
		{"fieldname": "current_batch", "label": _("Batch"), "fieldtype": "Link", "options": "Batch", "width": 120},
		{"fieldname": "photo", "label": _("Photo"), "fieldtype": "Data", "width": 100},
		{"fieldname": "missing_count", "label": _("Missing Count"), "fieldtype": "Int", "width": 110},
		{"fieldname": "completion", "label": _("Completion %"), "fieldtype": "Percent", "width": 120},
		{"fieldname": "missing_details", "label": _("Missing Details"), "fieldtype": "Data", "width": 450},
		{"fieldname": "contact_number", "label": _("Contact Number"), "fieldtype": "Data", "width": 140},
	]


def get_data(filters):
	conditions = {}
	for key in ("status", "standard", "current_batch", "school_name"):
		if filters.get(key):
			conditions[key] = filters.get(key)

	students = frappe.get_all(
		"Student",
		filters=conditions,
		fields=["name", "student_name", "standard", "current_batch", "father_mobile_number",
			"mother_mobile_number", *TRACKED_FIELDS],
		order_by="standard asc, current_batch asc, student_name asc",
	)

	only_field = filters.get("missing_field")
	photo_only = cint(filters.get("photo_missing_only"))
	total = len(TRACKED_FIELDS)
	data = []

	for s in students:
		missing = [f for f in TRACKED_FIELDS if is_blank(s.get(f))]
		if not missing:
			continue
		if photo_only and "image" not in missing:
			continue
		if only_field and only_field not in missing:
			continue

		data.append({
			"student": s.name,
			"student_name": s.student_name,
			"standard": s.standard,
			"current_batch": s.current_batch,
			"photo": _("Missing") if "image" in missing else _("Uploaded"),
			"missing_count": len(missing),
			"completion": flt((total - len(missing)) * 100.0 / total, 1),
			"missing_details": ", ".join(_(TRACKED_FIELDS[f]) for f in missing),
			"contact_number": s.preferred_whatsapp_number or s.father_mobile_number or s.mother_mobile_number,
		})

	return data


def is_blank(value):
	return value is None or not str(value).strip()
