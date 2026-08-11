# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class Group(Document):
	pass


def get_groups_for_standard(standard):
	"""Return the Group names mapped to the given Standard.

	`Group.standard_detail` is a Table MultiSelect, so the mapping lives as
	`Standard Detail` rows -- there is no `standard` column on `tabGroup`.
	Standard Detail is shared with Fee Structure, hence the parenttype filter.
	"""
	if not standard:
		return []

	names = frappe.get_all(
		"Standard Detail",
		filters={
			"parenttype": "Group",
			"parentfield": "standard_detail",
			"standard": standard,
		},
		pluck="parent",
		order_by="parent asc",
	)

	# a Group could list the same Standard twice; keep first-seen order
	return list(dict.fromkeys(names))


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_groups_by_standard(doctype, txt, searchfield, start, page_len, filters):
	"""Link-field query: only Groups mapped to filters["standard"].

	The parameter names/order are fixed by frappe.desk.search.search_widget,
	which calls this positionally as (doctype, txt, searchfield, start,
	page_len, filters).
	"""
	standard = (filters or {}).get("standard")
	if not standard:
		return []

	names = get_groups_for_standard(standard)

	if txt:
		needle = txt.lower()
		names = [name for name in names if needle in name.lower()]

	start = cint(start)
	page_len = cint(page_len) or 10

	return [[name] for name in names[start : start + page_len]]
