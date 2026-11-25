"""Call Not Attended: the parents who did not pick up.

Every ring nobody answered is a Parent Call Log with call_status "Not
Attended" (see pending_calls.log_not_attended). This screen lists them per
student and per screen the call was made from, for one month, and says
whether the parents were reached later the same month -- an Attended or
Closed log from the same screen after the last unanswered ring.
"""

import frappe
from frappe.utils import add_months, get_datetime, get_first_day, getdate, today

from bb_tution_management.bb_academy.pending_calls import (
	CALL_FOR,
	NOT_ATTENDED,
	_guard,
	_phones,
)


@frappe.whitelist()
def get_not_attended_calls(month=None, call_for=None, standard=None, batch=None, gender=None):
	_guard("read")

	first_day = get_first_day(getdate(f"{month}-01" if month and len(month) == 7 else (month or today())))
	values = {"first_day": first_day, "next_month": add_months(first_day, 1)}
	conditions = ["c.called_on >= %(first_day)s", "c.called_on < %(next_month)s"]
	if call_for:
		if call_for not in CALL_FOR:
			frappe.throw(frappe._("Unknown call screen {0}.").format(call_for))
		conditions.append("c.call_for = %(call_for)s")
		values["call_for"] = call_for
	for field, column, value in (
		("standard", "s.standard", standard),
		("batch", "s.current_batch", batch),
		("gender", "s.gender", gender),
	):
		if value:
			conditions.append(f"{column} = %({field})s")
			values[field] = value

	# Every call in the month from the students with at least one unanswered
	# ring, oldest first, so "reached later" can be read off in one pass.
	calls = frappe.db.sql(
		f"""
		SELECT c.name, c.student, c.call_for, c.call_status, c.called_on,
			c.called_by, c.spoken_to, c.call_notes
		FROM `tabParent Call Log` c
		LEFT JOIN `tabStudent` s ON s.name = c.student
		WHERE {" AND ".join(conditions)}
			AND (c.student, c.call_for) IN (
				SELECT student, call_for FROM `tabParent Call Log`
				WHERE call_status = %(not_attended)s
					AND called_on >= %(first_day)s AND called_on < %(next_month)s
			)
		ORDER BY c.called_on ASC, c.creation ASC
		""",
		{**values, "not_attended": NOT_ATTENDED},
		as_dict=True,
	)

	groups = {}
	for call in calls:
		key = (call.student, call.call_for)
		group = groups.setdefault(
			key,
			{"student": call.student, "call_for": call.call_for, "attempts": [], "reached": None},
		)
		if call.call_status == NOT_ATTENDED:
			group["attempts"].append(
				{
					"name": call.name,
					"called_on": call.called_on,
					"called_by": call.called_by,
					"spoken_to": call.spoken_to,
					"call_notes": call.call_notes,
				}
			)
			# A new ring after a reached call means they are unreachable again.
			group["reached"] = None
		elif group["attempts"]:
			group["reached"] = {
				"name": call.name,
				"status": call.call_status,
				"called_on": call.called_on,
				"called_by": call.called_by,
				"spoken_to": call.spoken_to,
			}

	students = {}
	if groups:
		for row in frappe.db.get_all(
			"Student",
			filters={"name": ("in", list({g["student"] for g in groups.values()}))},
			fields=[
				"name",
				"student_name",
				"standard",
				"current_batch",
				"gender",
				"image",
				"status",
				"father_name",
				"mother_name",
				"guardian_name",
				"father_mobile_number",
				"mother_mobile_number",
				"guardian_mobile_number",
				"preferred_mobile_number",
			],
		):
			students[row.name] = row

	rows = []
	for group in groups.values():
		student = students.get(group["student"]) or frappe._dict()
		last = group["attempts"][-1]
		rows.append(
			{
				**group,
				"key": f"{group['student']}::{group['call_for']}",
				"student_name": student.get("student_name") or group["student"],
				"standard": student.get("standard"),
				"batch": student.get("current_batch"),
				"gender": student.get("gender"),
				"image": student.get("image"),
				"student_status": student.get("status"),
				"father_name": student.get("father_name"),
				"mother_name": student.get("mother_name"),
				"guardian_name": student.get("guardian_name"),
				"phones": _phones(student) if student else [],
				"count": len(group["attempts"]),
				"last_called_on": last["called_on"],
				"is_pending": group["reached"] is None,
			}
		)

	# Still unreached first, the most rings on top, then the longest waiting.
	rows.sort(
		key=lambda r: (
			not r["is_pending"],
			-r["count"],
			get_datetime(r["last_called_on"]),
		)
	)

	return {
		"month": first_day,
		"rows": rows,
		"counts": {
			"pending": sum(1 for r in rows if r["is_pending"]),
			"reached": sum(1 for r in rows if not r["is_pending"]),
			"attempts": sum(r["count"] for r in rows),
		},
	}
