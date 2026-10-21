# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

"""Discontinued students counted per month, with the students listed under
each month. Months in the range with no discontinues still show, as 0."""

from collections import OrderedDict

from frappe import _
from frappe.utils import add_months, get_first_day, getdate

from bb_tution_management.bb_academy.discontinue import (
	get_discontinue_records,
	report_summary,
	student_columns,
)


def execute(filters=None):
	filters = filters or {}
	records = get_discontinue_records(filters)
	months = group_by_month(records, filters)

	return get_columns(), get_data(months), None, get_chart(months), report_summary(records)


def get_columns():
	return [
		{"fieldname": "label", "label": _("Month / Student"), "fieldtype": "Data", "width": 220},
		{"fieldname": "count", "label": _("Discontinued"), "fieldtype": "Int", "width": 110},
		{"fieldname": "reason_category", "label": _("Reason Category"), "fieldtype": "Data", "width": 180},
		*[c for c in student_columns() if c["fieldname"] != "student_name"],
	]


def group_by_month(records, filters):
	months = OrderedDict()

	# Pre-fill every month of the range so empty months show as 0.
	if filters.get("from_date") and filters.get("to_date"):
		month = get_first_day(filters.get("from_date"))
		while month <= getdate(filters.get("to_date")):
			months[month] = []
			month = add_months(month, 1)

	for r in records:
		months.setdefault(get_first_day(r["discontinued_date"]), []).append(r)

	return OrderedDict(sorted(months.items()))


def get_data(months):
	data = []
	for month, records in months.items():
		data.append({"label": month.strftime("%B %Y"), "count": len(records), "indent": 0})
		for r in records:
			data.append({**r, "label": r["student_name"], "indent": 1})
	return data


def get_chart(months):
	return {
		"data": {
			"labels": [m.strftime("%b %Y") for m in months],
			"datasets": [{"name": _("Discontinued"), "values": [len(r) for r in months.values()]}],
		},
		"type": "bar",
		"colors": ["#e24c4c"],
	}
