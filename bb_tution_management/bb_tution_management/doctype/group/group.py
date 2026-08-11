# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Group(Document):
	pass

@frappe.whitelist()
def get_groups_by_standard(*args, **kwargs):
	import json
	txt = kwargs.get('txt') or ''
	filters = kwargs.get('filters') or {}
	if isinstance(filters, str):
		filters = json.loads(filters)
	standard = filters.get('standard')
	if not standard:
		return []
	return frappe.db.sql("""
		select name, name from `tabGroup` 
		where name in (select parent from `tabStandard Detail` where standard = %s)
		and name like %s
	""", (standard, "%%%s%%" % txt))
