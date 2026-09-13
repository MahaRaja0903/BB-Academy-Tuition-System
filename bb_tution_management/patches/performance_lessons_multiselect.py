# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""Move the single `lesson` Link on the performance rows into `lessons`.

A day's teaching covers more than one lesson, so Lesson is now a Table
MultiSelect (`lessons` -> Lesson Item) rather than one Link. `bench migrate`
adds the child table but leaves whatever the old `lesson` column held sitting
where it was, so this patch copies each value across as the first — and for now
only — row of the multiselect. A row that already has lessons is left alone,
which is what makes a re-run safe.
"""

import frappe

PARENT_TYPES = (
	("Student Performance Tracker", "tabStudent Performance Tracker"),
	("Student Performance Session", "tabStudent Performance Session"),
)

PARENTFIELD = "lessons"


def execute():
	for doctype, table in PARENT_TYPES:
		if not _column_exists(table, "lesson"):
			continue
		_migrate(doctype, table)

	frappe.db.commit()


def _column_exists(table, column):
	"""An install created after the multiselect landed has nothing to migrate."""
	return bool(
		frappe.db.sql(
			"""
			SELECT 1 FROM information_schema.columns
			WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s
			""",
			(table, column),
		)
	)


def _migrate(doctype, table):
	rows = frappe.db.sql(
		f"""
		SELECT p.`name`, p.`lesson`
		FROM `{table}` p
		LEFT JOIN `tabLesson Item` li
			ON li.parent = p.`name` AND li.parenttype = %(doctype)s
			AND li.parentfield = %(parentfield)s
		WHERE IFNULL(p.`lesson`, '') != '' AND li.`name` IS NULL
		""",
		{"doctype": doctype, "parentfield": PARENTFIELD},
		as_dict=True,
	)

	for row in rows:
		# The old column was a Link, but an install that never ran the earlier
		# master migration can still hold free text. Anything that is not a real
		# Lesson is left in the column rather than turned into a broken row.
		if not frappe.db.exists("Lesson", row.lesson):
			continue

		frappe.get_doc(
			{
				"doctype": "Lesson Item",
				"lesson": row.lesson,
				"parent": row.name,
				"parenttype": doctype,
				"parentfield": PARENTFIELD,
				"idx": 1,
			}
		).db_insert()
