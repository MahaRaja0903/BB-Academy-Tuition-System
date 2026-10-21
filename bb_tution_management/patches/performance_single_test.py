# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""Fold Maths Test and Accounts Test into Test, and key every Test by its
Subject + Lesson + Portion combination.

A batch can now sit several Tests on one day, so a Test row is found through the
Test (session) it was graded on rather than by date alone. In order:

1. Every test row that never got its session link is pointed at the day's
   setup row it was graded under, while the old category is still on it.
2. Maths Test / Accounts Test rows and setups are renamed to Test. Document
   names are left alone — nothing looks a Test up by name any more.
3. Every Test setup and row gets the `test_key` of its combination.

Each step only touches rows that still need it, so a re-run is safe.
"""

import frappe

from bb_tution_management.bb_academy.performance_config import (
	RETIRED_TEST_CATEGORIES,
	combination_key,
	slug,
)
from bb_tution_management.bb_academy.syllabus import syllabus_of

TEST = "Test"
OLD_CATEGORIES = (TEST, *RETIRED_TEST_CATEGORIES)


def execute():
	_link_sessions()
	_rename_categories()
	_set_keys("Student Performance Session", "AND IFNULL(no_session, 0) = 0")
	_set_keys("Student Performance Tracker", "")
	frappe.db.commit()


def _link_sessions():
	rows = frappe.db.sql(
		"""
		SELECT name, date, standard, batch, category
		FROM `tabStudent Performance Tracker`
		WHERE category IN %(categories)s AND IFNULL(session, '') = ''
		""",
		{"categories": OLD_CATEGORIES},
		as_dict=True,
	)
	for row in rows:
		session = "SPS-{}-{}-{}-{}".format(
			row.date, slug(row.standard), slug(row.batch), slug(row.category)
		)
		if frappe.db.exists("Student Performance Session", session):
			frappe.db.set_value(
				"Student Performance Tracker", row.name, "session", session, update_modified=False
			)


def _rename_categories():
	for table in ("tabStudent Performance Tracker", "tabStudent Performance Session"):
		frappe.db.sql(
			f"UPDATE `{table}` SET category = %(test)s WHERE category IN %(old)s",
			{"test": TEST, "old": tuple(RETIRED_TEST_CATEGORIES)},
		)


def _set_keys(doctype, extra):
	names = frappe.db.sql_list(
		f"""
		SELECT name FROM `tab{doctype}`
		WHERE category = %(test)s AND IFNULL(test_key, '') = '' {extra}
		""",
		{"test": TEST},
	)
	for start in range(0, len(names), 500):
		chunk = names[start : start + 500]
		syllabus = syllabus_of(doctype, chunk)
		for name in chunk:
			frappe.db.set_value(
				doctype,
				name,
				"test_key",
				combination_key(syllabus.get(name, [])),
				update_modified=False,
			)
