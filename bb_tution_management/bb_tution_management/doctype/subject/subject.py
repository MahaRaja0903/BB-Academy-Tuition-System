# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class Subject(Document):
	def validate(self):
		self.subject_name = (self.subject_name or "").strip()
		if not self.subject_name:
			frappe.throw("Subject Name is required.")

		# A standard listed twice would show the subject twice in every dropdown.
		seen = set()
		rows = []
		for row in self.standard_applicable or []:
			if not row.standard or row.standard in seen:
				continue
			seen.add(row.standard)
			row.idx = len(rows) + 1
			rows.append(row)
		self.standard_applicable = rows


def subjects_for_standard(standard=None, txt=None):
	"""Subject names offered for `standard`.

	A Subject with an empty Standard Applicable table is treated as offered to
	every standard — that is how a subject taught across the school is set up,
	and it keeps the dropdown usable before the masters are fully filled in.
	"""
	conditions = []
	params = {}

	if standard:
		params["standard"] = standard
		conditions.append(
			"""(
				NOT EXISTS (
					SELECT 1 FROM `tabStandard Detail` d
					WHERE d.parent = s.name AND d.parenttype = 'Subject'
				)
				OR EXISTS (
					SELECT 1 FROM `tabStandard Detail` d
					WHERE d.parent = s.name AND d.parenttype = 'Subject'
						AND d.standard = %(standard)s
				)
			)"""
		)

	if txt:
		params["txt"] = f"%{txt}%"
		conditions.append("s.name LIKE %(txt)s")

	where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

	return frappe.db.sql_list(
		f"SELECT s.name FROM `tabSubject` s {where} ORDER BY s.name ASC", params
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def subject_link_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link-field search for `subject`, narrowed to the standard on the form."""
	standard = (filters or {}).get("standard")
	names = subjects_for_standard(standard, txt)
	start = cint(start)
	return [(name,) for name in names[start : start + (cint(page_len) or 20)]]
