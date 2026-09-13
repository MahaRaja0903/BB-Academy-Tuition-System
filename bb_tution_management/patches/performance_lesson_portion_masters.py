# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""Move the free-text Lesson and Portion off the performance rows into masters.

`lesson` used to be a Data field and `portion` a Small Text; they are now a Link
to Lesson and a Portion Item multiselect. `bench migrate` changes the field
definitions but leaves the old values sitting in the columns, so this patch
turns what teachers already typed into real master records and re-points the
rows at them. Anything it cannot map (a lesson typed without a subject, a
portion that is not in the master) is left in place rather than guessed at.
"""

import frappe

from bb_tution_management.bb_tution_management.doctype.lesson.lesson import lesson_docname
from bb_tution_management.bb_tution_management.doctype.portion.portion import (
	create_default_portions,
)

PARENT_TYPES = (
	("Student Performance Tracker", "tabStudent Performance Tracker"),
	("Student Performance Session", "tabStudent Performance Session"),
)


def execute():
	create_default_portions()
	_migrate_lessons()
	_migrate_portions()
	frappe.db.commit()


def _column_exists(table, column):
	"""An install that never had the old fields has nothing to migrate."""
	return bool(
		frappe.db.sql(
			"""
			SELECT 1 FROM information_schema.columns
			WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s
			""",
			(table, column),
		)
	)


def _migrate_lessons():
	for doctype, table in PARENT_TYPES:
		if not _column_exists(table, "lesson"):
			continue

		rows = frappe.db.sql(
			f"""
			SELECT DISTINCT `lesson`, `subject`, `standard`
			FROM `{table}`
			WHERE IFNULL(`lesson`, '') != '' AND IFNULL(`subject`, '') != ''
				AND IFNULL(`standard`, '') != ''
			""",
			as_dict=True,
		)

		for row in rows:
			title = (row.lesson or "").strip()
			if not title:
				continue

			name = lesson_docname(title, row.subject, row.standard)
			if row.lesson == name:
				# Already a Link value — a re-run of this patch.
				continue

			if not frappe.db.exists("Lesson", name):
				try:
					frappe.get_doc(
						{
							"doctype": "Lesson",
							"lesson_name": title,
							"subject": row.subject,
							"standard": row.standard,
						}
					).insert(ignore_permissions=True)
				except Exception:
					# A subject no longer offered for that standard fails Lesson's
					# own validation. Leave the text as it is rather than losing it.
					frappe.log_error(
						f"Could not create Lesson {title} ({row.subject} - {row.standard})",
						"Performance lesson migration",
					)
					continue

			frappe.db.sql(
				f"""
				UPDATE `{table}`
				SET `lesson` = %(name)s
				WHERE `lesson` = %(old)s AND `subject` = %(subject)s AND `standard` = %(standard)s
				""",
				{"name": name, "old": row.lesson, "subject": row.subject, "standard": row.standard},
			)


def _migrate_portions():
	for doctype, table in PARENT_TYPES:
		if not _column_exists(table, "portion"):
			continue

		rows = frappe.db.sql(
			f"SELECT `name`, `portion` FROM `{table}` WHERE IFNULL(`portion`, '') != ''",
			as_dict=True,
		)

		for row in rows:
			# The old field was free text; commas and slashes are how teachers
			# wrote more than one portion into it.
			names = []
			for part in str(row.portion).replace("/", ",").split(","):
				part = part.strip()
				if not part:
					continue
				existing = frappe.db.get_value("Portion", {"portion_name": part}, "name")
				if existing and existing not in names:
					names.append(existing)

			if not names:
				continue

			if frappe.db.exists(
				"Portion Item", {"parent": row.name, "parenttype": doctype, "parentfield": "portions"}
			):
				continue

			for idx, portion in enumerate(names, start=1):
				frappe.get_doc(
					{
						"doctype": "Portion Item",
						"portion": portion,
						"parent": row.name,
						"parenttype": doctype,
						"parentfield": "portions",
						"idx": idx,
					}
				).db_insert()
