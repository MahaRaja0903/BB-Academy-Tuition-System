# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""Carry the single `subject` on the performance rows into `subjects`.

A class can now cover more than one subject, so the rows list them in a
`subjects` multiselect (Subject Item) and each Portion Item names the subject it
was covered under. Every row saved before this had exactly one subject, so it
becomes the only row of `subjects`, and its portions are tagged with it. A row
that already has subjects is left alone, which is what makes a re-run safe.
"""

import frappe

PARENT_TYPES = (
	("Student Performance Tracker", "tabStudent Performance Tracker"),
	("Student Performance Session", "tabStudent Performance Session"),
)


def execute():
	for doctype, table in PARENT_TYPES:
		_migrate_subjects(doctype, table)
		_tag_portions(doctype, table)

	frappe.db.commit()


def _migrate_subjects(doctype, table):
	rows = frappe.db.sql(
		f"""
		SELECT p.`name`, p.`subject`
		FROM `{table}` p
		LEFT JOIN `tabSubject Item` si
			ON si.parent = p.`name` AND si.parenttype = %(doctype)s AND si.parentfield = 'subjects'
		WHERE IFNULL(p.`subject`, '') != '' AND si.`name` IS NULL
		""",
		{"doctype": doctype},
		as_dict=True,
	)

	for row in rows:
		frappe.get_doc(
			{
				"doctype": "Subject Item",
				"subject": row.subject,
				"parent": row.name,
				"parenttype": doctype,
				"parentfield": "subjects",
				"idx": 1,
			}
		).db_insert()


def _tag_portions(doctype, table):
	frappe.db.sql(
		f"""
		UPDATE `tabPortion Item` pi
		INNER JOIN `{table}` p ON p.`name` = pi.parent
		SET pi.`subject` = p.`subject`
		WHERE pi.parenttype = %(doctype)s AND pi.parentfield = 'portions'
			AND IFNULL(pi.`subject`, '') = '' AND IFNULL(p.`subject`, '') != ''
		""",
		{"doctype": doctype},
	)
