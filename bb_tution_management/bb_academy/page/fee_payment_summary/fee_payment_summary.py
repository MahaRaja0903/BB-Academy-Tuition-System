"""Fee Payment Summary dashboard: the data layer.

For one calendar month, every student's fee row for that month is split by
standard band (6th to 9th, 10th to 12th) and gender, and summed three ways:
what is due, what is settled, and what is still pending.

The fee ledger is the Student's `payment_details` table. Its rows carry a month
name but (mostly) no date, so the calendar year comes from the student's
Academic Year: the rows run in order from the year's start date. An academic
year can hold the same month twice (10th Std runs April to April), so the n-th
"April" row is matched to the n-th April inside that academic year.

Amounts follow `update_student_totals` on Fee Invoice, so a student's figures
here agree with the paid / pending totals on their record:
  - a month not yet invoiced is billed at `get_month_amount` (the monthly fee,
    pro-rata for a late-joining month);
  - Paid and Paid By Starting Payment months owe nothing;
  - pending is what is billed less what was paid and any discount;
  - "paid amount" is billed less pending, so Total = Paid + Pending.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice import (
	MONTH_NAMES,
	PAID_BY_STARTING_PAYMENT,
	REFUNDED,
	get_month_amount,
)

# Mirrors the roles on fee_payment_summary.json. Whitelisted methods can be
# called without opening the page, so they need their own check.
ALLOWED_ROLES = {"System Manager", "Administrator", "Accountant"}

# Months that were never owed (or were handed back) stay off the dashboard.
EXCLUDED_STATUSES = ("Not Joined", "No Fees", REFUNDED)

PAID_STATUSES = ("Paid", PAID_BY_STARTING_PAYMENT)

GENDERS = ("Boys", "Girls")

# Standard bands, by Standard.academic_order.
BANDS = (
	{"key": "6-9", "label": "6th To 9th Std", "from": 6, "to": 9},
	{"key": "10-12", "label": "10th To 12th Std", "from": 10, "to": 12},
)

STUDENT_STATUSES = ("Active", "All")


def _guard():
	if frappe.session.user == "Administrator":
		return
	if not (ALLOWED_ROLES & set(frappe.get_roles())):
		frappe.throw(_("You are not permitted to view this dashboard."), frappe.PermissionError)


def _band_for(order):
	order = cint(order)
	for band in BANDS:
		if band["from"] <= order <= band["to"]:
			return band["key"]
	return None


def _month_index(d):
	return d.year * 12 + d.month - 1


def _occurrence(ay_start, ay_end, year, month):
	"""Which occurrence (0-based) of `month` inside the academic year the
	target year/month is, or None when the academic year does not cover it."""
	start, end, target = _month_index(ay_start), _month_index(ay_end), year * 12 + month - 1
	if not start <= target <= end:
		return None
	return sum(1 for i in range(start, target) if i % 12 == month - 1)


@frappe.whitelist()
def get_years():
	"""Calendar years that some academic year touches, newest first."""
	_guard()
	row = frappe.db.sql(
		"select min(start_date), max(end_date) from `tabAcademic Year` where start_date is not null",
	)
	today = getdate(nowdate())
	first = row[0][0].year if row and row[0][0] else today.year
	last = row[0][1].year if row and row[0][1] else today.year
	first, last = min(first, today.year), max(last, today.year)
	return list(range(last, first - 1, -1))


@frappe.whitelist()
def get_summary(year=None, month=None, student_status="Active"):
	"""Due / paid / pending for one calendar month, by standard band and gender.

	year:  calendar year, e.g. 2026.
	month: 1-12.
	student_status: "Active" counts active students only, "All" everyone.
	"""
	_guard()

	today = getdate(nowdate())
	year = cint(year) or today.year
	month = cint(month) or today.month
	if not 1 <= month <= 12:
		frappe.throw(_("Month must be between 1 and 12."))
	if student_status not in STUDENT_STATUSES:
		student_status = "Active"
	month_name = MONTH_NAMES[month - 1]

	conditions = ["ay.start_date is not null", "ay.end_date is not null"]
	if student_status == "Active":
		conditions.append("s.status = 'Active'")

	students = frappe.db.sql(
		f"""
		select
			s.name, s.student_name, s.gender, s.standard, s.status, s.current_batch,
			coalesce(nullif(s.preferred_whatsapp_number, ''), nullif(s.father_mobile_number, ''),
				nullif(s.mother_mobile_number, ''), s.guardian_mobile_number) as mobile,
			s.monthly_fee, s.starting_payment, s.admission_date, s.rejoined_date,
			coalesce(st.academic_order, 0) as academic_order,
			ay.start_date as ay_start, ay.end_date as ay_end
		from `tabStudent` s
		inner join `tabAcademic Year` ay on ay.name = s.academic_year
		left join `tabStandard` st on st.name = s.standard
		where {" and ".join(conditions)}
		""",
		as_dict=True,
	)

	# Which of the student's `month_name` rows is the one for this year.
	wanted = {}
	for s in students:
		occ = _occurrence(getdate(s.ay_start), getdate(s.ay_end), year, month)
		if occ is not None:
			wanted[s.name] = occ

	rows_by_student = {}
	if wanted:
		for r in frappe.db.sql(
			"""
			select parent, idx, status, amount_need_to_pay, amount_paid, discount_amount
			from `tabStudent Payment Detail`
			where parenttype = 'Student' and parentfield = 'payment_details'
				and month = %(month)s and parent in %(students)s
			order by parent, idx
			""",
			{"month": month_name, "students": tuple(wanted)},
			as_dict=True,
		):
			rows_by_student.setdefault(r.parent, []).append(r)

	def blank_cell():
		return {
			"total_amount": 0.0, "total_count": 0,
			"paid_amount": 0.0, "paid_count": 0,
			"pending_amount": 0.0, "not_paid_count": 0,
			"paid_students": [], "not_paid_students": [],
		}

	cells = {(b["key"], g): blank_cell() for b in BANDS for g in GENDERS}
	skipped = 0

	for s in students:
		occ = wanted.get(s.name)
		rows = rows_by_student.get(s.name) or []
		if occ is None or occ >= len(rows):
			continue
		row = rows[occ]
		status = row.status or "Not Paid"
		if status in EXCLUDED_STATUSES:
			continue

		cell = cells.get((_band_for(s.academic_order), s.gender))
		if cell is None:
			skipped += 1
			continue

		billed = flt(row.amount_need_to_pay) or flt(get_month_amount(s, month_name))
		if status in PAID_STATUSES:
			pending = 0.0
		else:
			pending = max(0.0, billed - flt(row.amount_paid) - flt(row.discount_amount))
		paid = max(0.0, billed - pending)

		cell["total_amount"] += billed
		cell["total_count"] += 1
		cell["paid_amount"] += paid
		cell["pending_amount"] += pending

		entry = {
			"student": s.name,
			"student_name": s.student_name,
			"standard": s.standard,
			"batch": s.current_batch,
			"mobile": s.mobile,
			"status": status,
			"billed": billed,
			"paid": paid,
			"pending": pending,
		}
		if pending > 0:
			cell["not_paid_count"] += 1
			cell["not_paid_students"].append(entry)
		else:
			cell["paid_count"] += 1
			cell["paid_students"].append(entry)

	groups = []
	for band in BANDS:
		for gender in GENDERS:
			cell = cells[(band["key"], gender)]
			for key in ("paid_students", "not_paid_students"):
				cell[key].sort(key=lambda e: (-e["pending"], e["standard"] or "", e["student_name"] or ""))
			groups.append({"band": band["key"], "label": band["label"], "gender": gender, **cell})

	totals = {
		k: sum(g[k] for g in groups)
		for k in ("total_amount", "total_count", "paid_amount", "paid_count", "pending_amount", "not_paid_count")
	}

	return {
		"year": year,
		"month": month,
		"month_name": month_name,
		"student_status": student_status,
		"groups": groups,
		"totals": totals,
		"skipped": skipped,
	}
