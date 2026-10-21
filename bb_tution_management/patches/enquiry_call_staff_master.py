# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""Back the enquiry call log's "Call Works Done By" with the Enquiry Call Staff master.

The field used to be free text and is now a Link. Every name already typed into
it becomes a master record exactly as written, so no existing call log changes
meaning; spelling variants can be merged later from the master by renaming one
onto another with "Merge with existing". Only stray leading/trailing whitespace
is trimmed, because Frappe strips it from record names and a padded value would
then fail link validation the next time the enquiry is saved.
"""

import frappe


def execute():
	table = "tabEnquiry Call Log"
	if not frappe.db.table_exists("Enquiry Call Log"):
		return

	frappe.db.sql(
		f"""
		UPDATE `{table}`
		SET `call_works_done_by_s` = TRIM(`call_works_done_by_s`)
		WHERE `call_works_done_by_s` != TRIM(`call_works_done_by_s`)
		"""
	)

	names = frappe.db.sql_list(
		f"""
		SELECT DISTINCT `call_works_done_by_s` FROM `{table}`
		WHERE IFNULL(`call_works_done_by_s`, '') != ''
		"""
	)

	for name in names:
		if frappe.db.exists("Enquiry Call Staff", name):
			continue
		frappe.get_doc({"doctype": "Enquiry Call Staff", "staff_name": name}).insert(
			ignore_permissions=True
		)

	frappe.db.commit()
