# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

"""Discontinued students counted per Discontinue Reason, most common first,
with the students listed under each reason."""

from collections import defaultdict

from frappe import _
from frappe.utils import flt

from bb_tution_management.bb_academy.discontinue import (
	get_discontinue_records,
	report_summary,
	student_columns,
)


def execute(filters=None):
	filters = filters or {}
	records = get_discontinue_records(filters)
	reasons = group_by_reason(records)

	return get_columns(), get_data(reasons, len(records)), None, get_chart(reasons), report_summary(records)


def get_columns():
	return [
		{"fieldname": "label", "label": _("Reason / Student"), "fieldtype": "Data", "width": 240},
		{"fieldname": "count", "label": _("Students"), "fieldtype": "Int", "width": 100},
		{"fieldname": "share", "label": _("Share %"), "fieldtype": "Percent", "width": 100},
		*[c for c in student_columns() if c["fieldname"] != "student_name"],
	]


def group_by_reason(records):
	reasons = defaultdict(list)
	for r in records:
		reasons[r["reason_category"]].append(r)
	return sorted(reasons.items(), key=lambda item: (-len(item[1]), item[0]))


def get_data(reasons, total):
	data = []
	for reason, records in reasons:
		data.append({
			"label": reason,
			"count": len(records),
			"share": flt(len(records) * 100.0 / total, 1) if total else 0,
			"indent": 0,
		})
		for r in records:
			data.append({**r, "label": r["student_name"], "indent": 1})
	return data


def get_chart(reasons):
	return {
		"data": {
			"labels": [reason for reason, _records in reasons],
			"datasets": [{"name": _("Students"), "values": [len(records) for _reason, records in reasons]}],
		},
		"type": "donut",
	}
