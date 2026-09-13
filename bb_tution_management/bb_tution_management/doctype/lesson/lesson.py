# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint

from bb_tution_management.bb_tution_management.doctype.subject.subject import (
	subjects_for_standard,
)


def lesson_docname(lesson_name, subject, standard):
	"""The name a Lesson gets for a (lesson, subject, standard) triple.

	The same lesson title legitimately repeats across subjects and standards
	("Chapter 1" is in every book), so the name has to carry all three. "/"
	is the only character Frappe refuses outright in a name.
	"""
	raw = f"{lesson_name} ({subject} - {standard})"
	return raw.replace("/", "-").strip()


class Lesson(Document):
	def autoname(self):
		self.name = lesson_docname(
			(self.lesson_name or "").strip(), self.subject, self.standard
		)

	def validate(self):
		self.lesson_name = (self.lesson_name or "").strip()
		if not self.lesson_name:
			frappe.throw("Lesson is required.")

		# A lesson belongs to a subject that the standard is actually taught,
		# otherwise the Performance Manager would offer it under a subject the
		# dropdown there never shows.
		if self.subject not in subjects_for_standard(self.standard):
			frappe.throw(
				f"{self.subject} is not offered for {self.standard}. "
				f"Add {self.standard} to the subject's Standard Applicable list first.",
				title="Subject Not Offered",
			)

		expected = lesson_docname(self.lesson_name, self.subject, self.standard)
		if not self.is_new() and self.name != expected and frappe.db.exists("Lesson", expected):
			frappe.throw(
				f"{self.lesson_name} already exists for {self.subject} / {self.standard}.",
				title="Duplicate Lesson",
			)


def lessons_for(standard=None, subject=None, txt=None, include=None):
	"""Lesson names mapped to `standard` + `subject`, enabled ones first.

	`include` keeps lessons that are already saved on a record visible even when
	they have since been disabled or re-mapped — otherwise opening the record
	would silently drop them. It takes one name or a list of them.
	"""
	conditions = ["l.disabled = 0"]
	params = {}

	if standard:
		params["standard"] = standard
		conditions.append("l.standard = %(standard)s")
	if subject:
		params["subject"] = subject
		conditions.append("l.subject = %(subject)s")
	if txt:
		params["txt"] = f"%{txt}%"
		conditions.append("l.lesson_name LIKE %(txt)s")

	where = " AND ".join(conditions)
	rows = frappe.db.sql(
		f"""
		SELECT l.name, l.lesson_name, l.subject, l.standard
		FROM `tabLesson` l
		WHERE {where}
		ORDER BY IF(l.lesson_order = 0, 999999, l.lesson_order) ASC, l.lesson_name ASC
		""",
		params,
		as_dict=True,
	)

	if include:
		if isinstance(include, str):
			include = [include]
		listed = {r.name for r in rows}
		missing = [n for n in include if n and n not in listed]
		if missing:
			rows += frappe.get_all(
				"Lesson",
				filters={"name": ["in", missing]},
				fields=["name", "lesson_name", "subject", "standard"],
			)

	return rows


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def lesson_link_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link-field search for `lesson`, narrowed to the form's standard/subject."""
	filters = filters or {}
	rows = lessons_for(filters.get("standard"), filters.get("subject"), txt)
	start = cint(start)
	page_len = cint(page_len) or 20
	return [(r.name, r.lesson_name) for r in rows[start : start + page_len]]
