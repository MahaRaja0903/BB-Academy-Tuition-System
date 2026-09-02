# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt

from bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice import (
	SPLIT_UP,
	STARTING_PAYMENT,
)

# The forms the money can come in as. The Fee Invoice records which one was used;
# invoices taken before that field existed carry nothing against it, and all of
# those were collected in cash.
CASH = "Cash"
GPAY = "GPAY"
SCANNER = "Scanner"
PAYMENT_MODES = (CASH, GPAY, SCANNER)


def execute(filters=None):
	filters = frappe._dict(filters or {})

	rows = get_data(filters)
	totals = get_totals(rows)

	# Only ever needed to add the modes up; it is not a column.
	for row in rows:
		row.pop("mode_amounts", None)

	return get_columns(), rows + get_summary_rows(totals), None, None, get_report_summary(totals)


def get_columns():
	return [
		{"fieldname": "student_name", "label": _("Student Name"), "fieldtype": "Data", "width": 220},
		{"fieldname": "gender", "label": _("Gender"), "fieldtype": "Data", "width": 100},
		{"fieldname": "standard", "label": _("Standard"), "fieldtype": "Link", "options": "Standard", "width": 120},
		{"fieldname": "batch", "label": _("Batch"), "fieldtype": "Link", "options": "Batch", "width": 140},
		{"fieldname": "payment_method", "label": _("Payment Method"), "fieldtype": "Data", "width": 140},
		{"fieldname": "payment_type", "label": _("Payment Type"), "fieldtype": "Data", "width": 140},
		{"fieldname": "payment_time_and_date", "label": _("Payment Time and Date"), "fieldtype": "Datetime", "width": 180},
		{"fieldname": "amount_paid", "label": _("Amount Paid"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "balance_amount", "label": _("Balance Amount"), "fieldtype": "Currency", "width": 150},
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

	if filters.get("from_date"):
		conditions.append("fi.invoice_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("fi.invoice_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	standards = as_list(filters.get("standard"))
	if standards:
		conditions.append("s.standard in %(standards)s")
		values["standards"] = standards

	batches = as_list(filters.get("batch"))
	if batches:
		conditions.append("s.current_batch in %(batches)s")
		values["batches"] = batches

	if filters.get("gender"):
		conditions.append("s.gender = %(gender)s")
		values["gender"] = filters.get("gender")

	return (" and " + " and ".join(conditions)) if conditions else ""


def get_mode_amounts(invoice):
	"""How the invoice's paid amount came in, split across the payment modes.

	A Split Up invoice records the split against its Grand Total, so a part
	payment is shared out in that same proportion -- the modes always add back
	up to what was actually paid. Any other invoice came in as the single mode
	named on it, and an invoice from before the Payment Method field existed
	came in as cash.
	"""
	paid = flt(invoice.paid_amount)
	method = invoice.payment_method

	if method == SPLIT_UP:
		parts = [flt(invoice.cash), flt(invoice.gpay), flt(invoice.scanner)]
		recorded = sum(parts)

		if recorded > 0:
			if abs(recorded - paid) >= 0.01:
				# Shared out in the recorded proportion, with the rounding
				# remainder left on the last mode so the parts still add up.
				shared = [flt(paid * part / recorded, 2) for part in parts[:-1]]
				parts = shared + [flt(paid - sum(shared), 2)]

			return dict(zip(PAYMENT_MODES, parts))

		# Split Up with nothing recorded against it -- read it as cash rather
		# than dropping the payment out of the mode totals altogether.
		method = CASH

	amounts = {mode: 0.0 for mode in PAYMENT_MODES}
	amounts[method if method in (GPAY, SCANNER) else CASH] = paid

	return amounts


def get_data(filters):
	values = {"starting_payment": STARTING_PAYMENT}
	where_clause = get_conditions(filters, values)

	invoices = frappe.db.sql(
		"""
		select
			fi.name,
			fi.invoice_date,
			fi.creation,
			s.student_name,
			s.gender,
			s.standard,
			s.current_batch as batch,
			fi.paid_amount,
			fi.balance_amount,
			fi.payment_method,
			fi.cash,
			fi.gpay,
			fi.scanner,
			ifnull(fi.is_starting_fee, 0) as is_starting_fee,
			exists (
				select 1 from `tabFees Invoice Details` fd
				where fd.parent = fi.name
					and fd.parenttype = 'Fee Invoice'
					and fd.month = %(starting_payment)s
			) as has_starting_row
		from `tabFee Invoice` fi
		inner join `tabStudent` s on s.name = fi.student
		where fi.docstatus = 1
			{where_clause}
		order by fi.invoice_date asc, s.standard asc, s.student_name asc, fi.name asc
		""".format(where_clause=where_clause),
		values,
		as_dict=True,
	)

	fee_type = filters.get("fee_type")
	payment_method = filters.get("payment_method")

	data = []
	for invoice in invoices:
		# The starting payment is told apart either by the flag on the invoice or
		# by the month its Fees Details row is stored under -- older invoices
		# only carry one of the two.
		is_starting = bool(invoice.is_starting_fee or invoice.has_starting_row)
		if fee_type == STARTING_PAYMENT and not is_starting:
			continue
		if fee_type == "Monthly" and is_starting:
			continue

		amounts = get_mode_amounts(invoice)

		# Filtering by a mode keeps every payment that came in that way, a Split
		# Up that was partly collected in it included.
		if payment_method and flt(amounts.get(payment_method)) <= 0:
			continue

		data.append(
			frappe._dict(
				student_name=invoice.student_name,
				gender=invoice.gender,
				standard=invoice.standard,
				batch=invoice.batch,
				payment_method=invoice.payment_method,
				payment_type="Starting Payment" if is_starting else "Monthly",
				payment_time_and_date=invoice.creation,
				amount_paid=flt(invoice.paid_amount),
				balance_amount=flt(invoice.balance_amount),
				mode_amounts=amounts,
			)
		)

	return data


def get_totals(rows):
	totals = frappe._dict(
		final_total=0.0,
		balance_total=0.0,
		balance_count=0,
		mode_totals={mode: 0.0 for mode in PAYMENT_MODES},
		mode_counts={mode: 0 for mode in PAYMENT_MODES},
	)

	for row in rows:
		totals.final_total += flt(row.amount_paid)

		if flt(row.balance_amount) > 0:
			totals.balance_total += flt(row.balance_amount)
			totals.balance_count += 1

		for mode, amount in row.mode_amounts.items():
			if flt(amount) > 0:
				totals.mode_totals[mode] += flt(amount)
				totals.mode_counts[mode] += 1

	return totals


def get_summary_rows(totals):
	"""The totals repeated at the foot of the table, so they travel with an
	export or a print the way the summary cards above it do not.

	Each count rides in its own row's label -- the amount columns are money, and
	a count formatted as money reads as an amount."""
	summary = [
		frappe._dict(
			student_name=_("Final Total"),
			amount_paid=totals.final_total,
			is_summary=1,
		),
		frappe._dict(
			student_name=_("Balance Total (Count: {0})").format(totals.balance_count),
			balance_amount=totals.balance_total,
			is_summary=1,
		),
	]

	for mode in PAYMENT_MODES:
		summary.append(
			frappe._dict(
				student_name=_("{0} Total (Count: {1})").format(
					_(mode), totals.mode_counts[mode]
				),
				amount_paid=totals.mode_totals[mode],
				is_summary=1,
			)
		)

	# A blank line so the totals read as a block of their own rather than as
	# another student's payment.
	return [frappe._dict(is_summary=1)] + summary


def get_report_summary(totals):
	currency = frappe.db.get_default("currency") or "INR"

	def money(label, value, indicator="Blue"):
		return {
			"label": label,
			"value": value,
			"datatype": "Currency",
			"currency": currency,
			"indicator": indicator,
		}

	def count(label, value):
		return {"label": label, "value": value, "datatype": "Int", "indicator": "Grey"}

	return [
		money(_("Final Total"), totals.final_total, "Green"),
		money(_("Balance Total"), totals.balance_total, "Red" if totals.balance_total else "Green"),
		count(_("Balance Count"), totals.balance_count),
		money(_("Cash Total"), totals.mode_totals[CASH]),
		count(_("Cash Count"), totals.mode_counts[CASH]),
		money(_("GPay Total"), totals.mode_totals[GPAY]),
		count(_("GPay Count"), totals.mode_counts[GPAY]),
		money(_("Scanner Total"), totals.mode_totals[SCANNER]),
		count(_("Scanner Count"), totals.mode_counts[SCANNER]),
	]
