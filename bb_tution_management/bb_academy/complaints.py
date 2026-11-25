"""Parent complaints taken on follow-up calls, and the call back that solves them.

A complaint is raised from the Student Mistakes or Attendance Calls card. While
it is Open, that card cannot be closed; it is followed up on the Complaint
Calls screen, where staff call the parents again, record how it was solved,
and the complaint becomes Resolved.
"""

import frappe
from frappe.utils import add_months, get_first_day, getdate, now_datetime, today

DOCTYPE = "Parent Complaint"
OPEN, RESOLVED = "Open", "Resolved"
SOURCES = ("Attendance", "Mistakes")
COMPLAINED_BY = ("Father", "Mother", "Guardian", "Other")


def _guard(ptype="read"):
	if not frappe.has_permission(DOCTYPE, ptype):
		frappe.throw(
			frappe._("Not permitted to {0} Parent Complaints").format(ptype),
			frappe.PermissionError,
		)


def open_complaints(students=None, complaint_for=None, reference_name=None):
	"""Open complaints, counted per student (or for one reference)."""
	conditions = ["status = %(status)s"]
	values = {"status": OPEN}
	if students is not None:
		students = [s for s in students if s]
		if not students:
			return {}
		conditions.append("student IN %(students)s")
		values["students"] = tuple(students)
	if complaint_for:
		conditions.append("complaint_for = %(complaint_for)s")
		values["complaint_for"] = complaint_for
	if reference_name:
		conditions.append("reference_name = %(reference_name)s")
		values["reference_name"] = reference_name
	return {
		row[0]: row[1]
		for row in frappe.db.sql(
			f"""
			SELECT student, COUNT(name) FROM `tabParent Complaint`
			WHERE {" AND ".join(conditions)} GROUP BY student
			""",
			values,
		)
	}


def has_open_complaint(student=None, complaint_for=None, reference_name=None):
	students = [student] if student else None
	return bool(open_complaints(students, complaint_for, reference_name))


@frappe.whitelist()
def raise_complaint(
	student,
	complaint_for,
	complained_by,
	complaint,
	received_by=None,
	received_on=None,
	reference_doctype=None,
	reference_name=None,
):
	_guard("create")
	if complaint_for not in SOURCES:
		frappe.throw(frappe._("Unknown screen {0}.").format(complaint_for))
	if complained_by not in COMPLAINED_BY:
		frappe.throw(frappe._("Say who complained."))
	if not (complaint or "").strip():
		frappe.throw(frappe._("Write down what the parent said."))
	if reference_doctype and reference_doctype not in ("Student Mistake Record",):
		frappe.throw(frappe._("Unsupported reference."))

	doc = frappe.new_doc(DOCTYPE)
	doc.update(
		{
			"student": student,
			"complaint_for": complaint_for,
			"complained_by": complained_by,
			"complaint": complaint,
			"received_by": received_by or None,
			"received_on": received_on or now_datetime(),
			"reference_doctype": reference_doctype if reference_name else None,
			"reference_name": reference_name or None,
			"status": OPEN,
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def resolve_complaint(name, resolved_by=None, resolution_notes=None, resolution_spoken_to=None, resolved_on=None):
	"""The call back: record how it was solved and take it off the pending list."""
	_guard("write")
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.status == RESOLVED:
		frappe.throw(frappe._("This complaint is already solved."))
	doc.status = RESOLVED
	doc.resolved_by = resolved_by
	doc.resolution_notes = resolution_notes
	doc.resolution_spoken_to = resolution_spoken_to or None
	doc.resolved_on = resolved_on or now_datetime()
	doc.save(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def reopen_complaint(name):
	_guard("write")
	doc = frappe.get_doc(DOCTYPE, name)
	doc.status = OPEN
	doc.resolved_on = None
	doc.resolved_by = None
	doc.resolution_notes = None
	doc.resolution_spoken_to = None
	doc.save(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def get_complaints(month=None, complaint_for=None, standard=None, batch=None, gender=None):
	"""Every Open complaint (whatever month it came in), plus the complaints
	received or solved in `month`. The screen splits them into Pending and
	Completed; the counts are worked out here so the cards agree with the list."""
	_guard("read")

	first_day = get_first_day(getdate(f"{month}-01" if month and len(month) == 7 else (month or today())))
	values = {"first_day": first_day, "next_month": add_months(first_day, 1), "open": OPEN}
	conditions = [
		"""(c.status = %(open)s
			OR (c.received_on >= %(first_day)s AND c.received_on < %(next_month)s)
			OR (c.resolved_on >= %(first_day)s AND c.resolved_on < %(next_month)s))"""
	]
	for field, column, value in (
		("complaint_for", "c.complaint_for", complaint_for),
		("standard", "c.standard", standard),
		("batch", "c.batch", batch),
		("gender", "s.gender", gender),
	):
		if value:
			conditions.append(f"{column} = %({field})s")
			values[field] = value

	rows = frappe.db.sql(
		f"""
		SELECT c.name, c.student, c.student_name, c.standard, c.batch, c.status,
			c.complaint_for, c.reference_doctype, c.reference_name,
			c.complained_by, c.complaint, c.received_on, c.received_by,
			c.resolution_spoken_to, c.resolved_on, c.resolved_by, c.resolution_notes,
			s.gender, s.image, s.father_name, s.mother_name, s.guardian_name,
			s.father_mobile_number, s.mother_mobile_number, s.guardian_mobile_number,
			s.preferred_mobile_number
		FROM `tabParent Complaint` c
		LEFT JOIN `tabStudent` s ON s.name = c.student
		WHERE {" AND ".join(conditions)}
		ORDER BY (c.status = %(open)s) DESC, c.received_on ASC
		""",
		values,
		as_dict=True,
	)

	from bb_tution_management.bb_academy.pending_calls import _phones

	def in_month(value):
		return bool(value) and first_day <= getdate(value) < values["next_month"]

	for row in rows:
		row["phones"] = _phones(row)
		row["received_this_month"] = in_month(row.received_on)
		for key in (
			"father_mobile_number",
			"mother_mobile_number",
			"guardian_mobile_number",
			"preferred_mobile_number",
		):
			row.pop(key, None)

	return {
		"month": first_day,
		"complaints": rows,
		"counts": {
			"pending": sum(1 for r in rows if r.status == OPEN),
			"completed": sum(1 for r in rows if r.status == RESOLVED and in_month(r.resolved_on)),
			"total": sum(1 for r in rows if r.received_this_month),
		},
	}
