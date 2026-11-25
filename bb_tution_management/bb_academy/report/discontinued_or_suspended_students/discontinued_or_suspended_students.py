# Copyright (c) 2026, Maha Raja and contributors
# For license information, please see license.txt

"""Discontinued or Suspended Students.

Fee columns:
  * Starting Payment: the status of the student's "Starting Payment" ledger row
    (Student > Payment Details) and what is still pending on it.
  * Last Month Fee: the fee of the month the student was discontinued /
    suspended in. A student who attended at least MIN_DAYS_FOR_FEE days that
    month owes the month's fee, so an unpaid month shows "Not Paid". Fewer days
    attended means the month is not charged ("Below 5 Days").
  * Total To Pay: Starting Payment Pending + Last Month Fee Pending.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from bb_tution_management.bb_academy.page.fees_report.fees_report import (
	MONTH_NUMBER,
	_next_period,
)

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

STARTING = "Starting Payment"
MIN_DAYS_FOR_FEE = 5
ATTENDED_STATUSES = ("Present", "Late", "Early Outs")
PAID_LIKE = {"Paid": "Paid", "Paid By Starting Payment": "Paid By Starting Payment", "No Fees": "No Fees"}


def execute(filters=None):
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"fieldname": "student", "label": _("Student"), "fieldtype": "Link", "options": "Student", "width": 120},
		{"fieldname": "student_name", "label": _("Student Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "standard", "label": _("Standard"), "fieldtype": "Link", "options": "Standard", "width": 100},
		{"fieldname": "current_batch", "label": _("Batch"), "fieldtype": "Link", "options": "Batch", "width": 120},
		{"fieldname": "school_name", "label": _("School Name"), "fieldtype": "Link", "options": "School", "width": 160},
		{"fieldname": "gender", "label": _("Gender"), "fieldtype": "Data", "width": 80},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "month", "label": _("Month"), "fieldtype": "Data", "width": 120},
		{"fieldname": "starting_payment_status", "label": _("Starting Payment"), "fieldtype": "Data", "width": 130},
		{"fieldname": "starting_payment_pending", "label": _("Starting Payment Pending"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "days_attended", "label": _("Days Attended (Last Month)"), "fieldtype": "Int", "width": 110},
		{"fieldname": "last_month_fee_status", "label": _("Last Month Fee"), "fieldtype": "Data", "width": 150},
		{"fieldname": "last_month_fee_pending", "label": _("Last Month Fee Pending"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_to_pay", "label": _("Total To Pay"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "reason", "label": _("Reason"), "fieldtype": "Data", "width": 250},
	]


def _as_list(value):
	if not value:
		return []
	if isinstance(value, str):
		value = frappe.parse_json(value) if value.startswith("[") else [value]
	return [v for v in value if v]


def get_data(filters):
	filters = frappe._dict(filters or {})
	conditions = []
	values = {}

	if filters.get("status"):
		conditions.append("status = %(status)s")
		values["status"] = filters.get("status")
	else:
		conditions.append("status IN ('Discontinued', 'Suspended')")

	standards = _as_list(filters.get("standard"))
	if standards:
		conditions.append("standard IN %(standards)s")
		values["standards"] = tuple(standards)

	for field in ("current_batch", "gender"):
		if filters.get(field):
			conditions.append(f"{field} = %({field})s")
			values[field] = filters.get(field)

	# Effective date depends on the status
	status_date = "(CASE WHEN status = 'Discontinued' THEN discontinued__date ELSE suspended_date END)"

	if filters.get("month") in MONTHS:
		conditions.append(f"MONTH({status_date}) = %(month)s")
		values["month"] = MONTHS.index(filters.get("month")) + 1

	if filters.get("year"):
		conditions.append(f"YEAR({status_date}) = %(year)s")
		values["year"] = int(filters.get("year"))

	students = frappe.db.sql(f"""
		SELECT
			s.name as student, s.student_name, s.standard, s.current_batch, s.school_name,
			s.gender, s.status, s.discontinued__date, s.suspended_date,
			s.discontinued_reason, s.suspended_reason,
			s.starting_payment, s.monthly_fee, s.scholarship_student, s.yearly_fees_student,
			s.admission_date, ay.start_date as ay_start
		FROM `tabStudent` s
		LEFT JOIN `tabAcademic Year` ay ON ay.name = s.academic_year
		WHERE {' AND '.join(conditions)}
		ORDER BY {status_date} DESC, s.creation DESC
	""", values, as_dict=1)

	if not students:
		return []

	names = [s.student for s in students]
	ledger = _ledger_by_student(names)
	attendance = _attendance_by_student_month(names)

	data = []
	for s in students:
		if s.status == "Discontinued":
			date, reason = s.discontinued__date, s.discontinued_reason
		else:
			date, reason = s.suspended_date, s.suspended_reason
		date = getdate(date) if date else None

		rows = ledger.get(s.student, [])
		start_status, start_pending = _starting_payment(s, rows)
		days, fee_status, fee_pending = _last_month_fee(s, rows, date, attendance)

		data.append({
			"student": s.student,
			"student_name": s.student_name,
			"standard": s.standard,
			"current_batch": s.current_batch,
			"school_name": s.school_name,
			"gender": s.gender,
			"status": s.status,
			"date": date,
			"month": f"{MONTHS[date.month - 1]} {date.year}" if date else None,
			"starting_payment_status": start_status,
			"starting_payment_pending": start_pending,
			"days_attended": days,
			"last_month_fee_status": fee_status,
			"last_month_fee_pending": fee_pending,
			"total_to_pay": flt(start_pending) + flt(fee_pending),
			"reason": reason,
		})

	return data


def _ledger_by_student(names):
	out = {}
	for r in frappe.db.sql("""
		SELECT parent, month, status, amount_need_to_pay, amount_paid, pending,
			discount_amount, coupon_amount
		FROM `tabStudent Payment Detail`
		WHERE parenttype = 'Student' AND parentfield = 'payment_details' AND parent IN %(names)s
		ORDER BY parent, idx
	""", {"names": tuple(names)}, as_dict=1):
		out.setdefault(r.parent, []).append(r)
	return out


def _attendance_by_student_month(names):
	"""{(student, year, month): days attended}"""
	return {
		(r.student, cint(r.y), cint(r.m)): cint(r.days)
		for r in frappe.db.sql("""
			SELECT student, YEAR(attendance_date) as y, MONTH(attendance_date) as m,
				COUNT(DISTINCT attendance_date) as days
			FROM `tabStudent Attendance`
			WHERE student IN %(names)s AND status IN %(statuses)s AND docstatus < 2
			GROUP BY student, YEAR(attendance_date), MONTH(attendance_date)
		""", {"names": tuple(names), "statuses": ATTENDED_STATUSES}, as_dict=1)
	}


def _balance(row, expected):
	"""What is still owed on a ledger row: its stored pending, else the expected
	amount less what was paid, discounted or covered by a coupon."""
	if flt(row.pending) > 0:
		return flt(row.pending)
	return max(flt(expected) - flt(row.amount_paid) - flt(row.discount_amount) - flt(row.coupon_amount), 0)


def _starting_payment(s, rows):
	if cint(s.yearly_fees_student):
		return _("Yearly Fee Student"), 0
	row = next((r for r in rows if r.month == STARTING), None)
	if not row:
		return (_("Not Paid"), flt(s.starting_payment)) if flt(s.starting_payment) else (_("No Entry"), 0)
	if row.status in PAID_LIKE:
		return _(PAID_LIKE[row.status]), 0
	if row.status in ("Partial", "Reserved", "Not Paid"):
		pending = _balance(row, flt(row.amount_need_to_pay) or flt(s.starting_payment))
		return (_("Partial") if flt(row.amount_paid) else _("Not Paid")), pending
	return _(row.status or "No Entry"), 0


def _month_row(s, rows, year, month):
	"""Ledger row for (year, month), placing month names on the calendar by
	walking them from the Academic Year's start (like the Fees Report)."""
	monthly = [r for r in rows if r.month != STARTING and MONTH_NUMBER.get(r.month)]
	start = s.ay_start or s.admission_date
	if not start:
		matches = [r for r in monthly if MONTH_NUMBER[r.month] == month]
		return matches[-1] if matches else None
	start = getdate(start)
	cursor = (start.year, start.month)
	for r in monthly:
		period = _next_period(cursor, MONTH_NUMBER[r.month])
		cursor = (period[0] + 1, 1) if period[1] == 12 else (period[0], period[1] + 1)
		if period == (year, month):
			return r
	return None


def _last_month_fee(s, rows, date, attendance):
	if not date:
		return 0, None, 0
	days = attendance.get((s.student, date.year, date.month), 0)
	if cint(s.yearly_fees_student):
		return days, _("Yearly Fee Student"), 0

	row = _month_row(s, rows, date.year, date.month)
	if row and row.status in PAID_LIKE:
		return days, _(PAID_LIKE[row.status]), 0
	if cint(s.scholarship_student):
		return days, _("Scholarship"), 0
	if days < MIN_DAYS_FOR_FEE:
		return days, _("Below {0} Days").format(MIN_DAYS_FOR_FEE), 0

	if not row:
		return days, _("Not Paid"), flt(s.monthly_fee)
	pending = _balance(row, flt(s.monthly_fee) or flt(row.amount_need_to_pay))
	return days, (_("Partial") if flt(row.amount_paid) else _("Not Paid")), pending
