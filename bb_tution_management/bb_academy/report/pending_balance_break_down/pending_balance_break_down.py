# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt

from bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice import (
	MONTH_NAMES,
	SETTLED_STATUSES,
	STARTING_PAYMENT,
	get_academic_months,
)

# On top of the months the invoice already treats as settled, a month marked
# No Fees is not money the academy is waiting for -- it is a month the student
# was given free, so nothing is owed for it whatever fee they are otherwise on.
NOTHING_OWED_STATUSES = SETTLED_STATUSES + ("No Fees",)

# Starting Payment first, then the months in calendar order -- the fallback for
# a student with no academic year of their own to order by.
MONTH_ORDER = {month: idx for idx, month in enumerate([STARTING_PAYMENT] + MONTH_NAMES)}


def get_month_order(academic_year, _cache={}):
	"""Where each month sits in a student's own academic year.

	Standards here run on different years -- June to April, April to March --
	so a June starter's months read in the wrong order against a plain calendar.
	The starting payment always comes first.
	"""
	if academic_year not in _cache:
		months = get_academic_months(academic_year)
		_cache[academic_year] = (
			{month: idx for idx, month in enumerate([STARTING_PAYMENT] + months)}
			if months else MONTH_ORDER
		)

	return _cache[academic_year]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"fieldname": "student", "label": _("Student ID"), "fieldtype": "Link", "options": "Student", "width": 120},
		{"fieldname": "student_name", "label": _("Student Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "standard", "label": _("Standard"), "fieldtype": "Link", "options": "Standard", "width": 120},
		{"fieldname": "batch", "label": _("Batch"), "fieldtype": "Link", "options": "Batch", "width": 120},
		{"fieldname": "pending_amount", "label": _("Pending Fees Amount"), "fieldtype": "Currency", "width": 160},
		{"fieldname": "month", "label": _("Month"), "fieldtype": "Data", "width": 140},
		{"fieldname": "student_status", "label": _("Student Status"), "fieldtype": "Data", "width": 130},
	]


def as_list(value):
	"""A MultiSelectList filter arrives as a list, but as JSON text over the API
	and as a bare string when only one value was picked."""
	if not value:
		return []

	if isinstance(value, str):
		value = value.strip()
		if not value.startswith("["):
			return [value]
		try:
			value = json.loads(value)
		except ValueError:
			return []

	return [v for v in value if v]


def get_conditions(filters, values):
	conditions = []
	student_conditions = []

	standards = as_list(filters.get("standard"))
	if standards:
		cond = "s.standard in %(standards)s"
		conditions.append(cond)
		student_conditions.append(cond)
		values["standards"] = standards

	batches = as_list(filters.get("batch"))
	if batches:
		cond = "s.current_batch in %(batches)s"
		conditions.append(cond)
		student_conditions.append(cond)
		values["batches"] = batches

	if filters.get("gender"):
		cond = "s.gender = %(gender)s"
		conditions.append(cond)
		student_conditions.append(cond)
		values["gender"] = filters.get("gender")

	# The starting payment sits in the same table as the months, told apart only
	# by the month name it is stored under.
	if filters.get("fee_type") == STARTING_PAYMENT:
		conditions.append("spd.month = %(starting_payment_month)s")
	elif filters.get("fee_type") == "Monthly":
		conditions.append("spd.month != %(starting_payment_month)s")

	return (
		(" and " + " and ".join(conditions)) if conditions else "",
		(" and " + " and ".join(student_conditions)) if student_conditions else "",
	)


def get_data(filters):
	values = {
		"settled": NOTHING_OWED_STATUSES,
		"starting_payment_month": STARTING_PAYMENT,
	}
	where_clause, student_where_clause = get_conditions(filters, values)
	fee_type = filters.get("fee_type")

	rows = []
	if not fee_type or fee_type in (STARTING_PAYMENT, "Monthly"):
		rows.extend(frappe.db.sql(
			"""
			select
				s.name as student,
				s.student_name,
				s.standard,
				s.current_batch as batch,
				s.status as student_status,
				s.academic_year,
				spd.month,
				spd.amount_need_to_pay,
				spd.amount_paid
			from `tabStudent Payment Detail` spd
			inner join `tabStudent` s on s.name = spd.parent
			where spd.parenttype = 'Student'
				and ifnull(spd.month, '') != ''
				and ifnull(spd.status, '') not in %(settled)s
				and ifnull(s.yearly_fees_student, 0) = 0
				{where_clause}
			""".format(where_clause=where_clause),
			values,
			as_dict=True,
		))

	if not fee_type or fee_type == "Yearly Fees":
		rows.extend(frappe.db.sql(
			"""
			select
				s.name as student,
				s.student_name,
				s.standard,
				s.current_batch as batch,
				s.status as student_status,
				s.academic_year,
				'Yearly Fees' as month,
				s.yearly_fees_pending_amount as amount_need_to_pay,
				0 as amount_paid
			from `tabStudent` s
			where s.yearly_fees_student = 1
				and s.yearly_fees_pending_amount > 0
				{student_where_clause}
			""".format(student_where_clause=student_where_clause),
			values,
			as_dict=True,
		))

	data = []
	for row in rows:
		# Only ever what the table itself records: the amount the month was
		# actually billed, less what came in. Nothing is inferred from the fee
		# the student is nominally on -- some students are on free education, so
		# a month with no amount against it is a month with nothing to collect.
		pending = flt(row.amount_need_to_pay) - flt(row.amount_paid)
		if pending <= 0:
			continue

		data.append(
			frappe._dict(
				academic_year=row.academic_year,
				student=row.student,
				student_name=row.student_name,
				standard=row.standard,
				batch=row.batch,
				pending_amount=pending,
				month=row.month,
				student_status=row.student_status,
			)
		)

	data.sort(
		key=lambda row: (
			row.standard or "",
			row.batch or "",
			row.student_name or "",
			get_month_order(row.academic_year).get(row.month, 99),
		)
	)

	for row in data:
		row.pop("academic_year", None)

	return data
