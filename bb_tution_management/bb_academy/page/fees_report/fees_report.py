"""Starting Payment & Monthly Fees report: the data layer.

Every figure comes from the Student `payment_details` table, the ledger the fee
invoices keep up to date. It has one "Starting Payment" row plus one row per
month of the student's Academic Year.

Year / month of a row:
  * Starting Payment: the year of the student's Admission Date (or the row's
    date when there is no admission date). It applies to every month, so the
    Month filter never narrows it; only the Year filter does.
  * Monthly rows only carry a month name, so the calendar year is worked out by
    walking the rows in order from the Academic Year's start date. An
    "April to April" year therefore puts its first April in the start year and
    its second April in the next one.

Which rows count:
  * Paid                          -> paid
  * Not Paid / Partial / Reserved -> pending (to be collected) for Active students,
                                     including months that are not due yet, so
                                     picking an upcoming month shows what is
                                     still to be collected for it
  * Anything else (Not Joined, No Fees, Paid By Starting Payment, Refunded) is
    left out: there is nothing to collect for it, and months covered by the
    starting payment are already counted in the starting payment.

Pending amount of a row:
  * Partial / Reserved rows keep the balance stored on the row.
  * Not Paid monthly rows use the student's current Monthly Fee, which the
    Student form keeps in step with the Fee Structure for their standard and
    current batch (or a manually entered fee). The amount stored on the row can
    be stale after a batch change.
  * Not Paid starting payment rows use the row amount, else the student's
    Starting Payment.
  * Yearly-fee and scholarship students owe nothing month by month.

Total = Paid + Pending. Paid Amount also includes what has been collected on
Partial rows, so the three cards always add up.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

# Mirrors the roles on fees_report.json. Whitelisted methods can be called
# without opening the page, so they need their own check.
ALLOWED_ROLES = {"System Manager", "Administrator", "Accountant", "Receptionist"}

MONTH_NAMES = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December",
]
MONTH_NUMBER = {name: i + 1 for i, name in enumerate(MONTH_NAMES)}

STARTING = "Starting Payment"
PAID_STATUSES = {"Paid"}
PENDING_STATUSES = {"Not Paid", "Partial", "Reserved"}

SECTIONS = ("starting", "monthly", "overall")
KINDS = ("total", "paid", "pending")


def _guard():
	if frappe.session.user == "Administrator":
		return
	if not (ALLOWED_ROLES & set(frappe.get_roles())):
		frappe.throw(_("You are not permitted to view this report."), frappe.PermissionError)


def _ledger_rows():
	return frappe.db.sql(
		"""
		select
			s.name as student, s.student_name, s.status as student_status,
			s.standard, s.admission_date, s.monthly_fee, s.starting_payment,
			s.yearly_fees_student, s.scholarship_student, s.current_batch,
			ay.start_date as ay_start,
			d.month, d.status, d.date, d.amount_need_to_pay, d.amount_paid, d.pending
		from `tabStudent` s
		inner join `tabStudent Payment Detail` d
			on d.parent = s.name and d.parenttype = 'Student' and d.parentfield = 'payment_details'
		left join `tabAcademic Year` ay on ay.name = s.academic_year
		order by s.name, d.idx
		""",
		as_dict=True,
	)


def _next_period(cursor, month_num):
	"""First (year, month) on or after `cursor` whose month is `month_num`."""
	year = cursor[0] if month_num >= cursor[1] else cursor[0] + 1
	return year, month_num


def _entries():
	"""Ledger rows that count, each tagged with its (year, month) and amounts."""
	entries = []
	cursor, last_student = None, None

	for r in _ledger_rows():
		if r.student != last_student:
			last_student = r.student
			start = getdate(r.ay_start) if r.ay_start else None
			cursor = (start.year, start.month) if start else None

		is_starting = r.month == STARTING
		if is_starting:
			when = r.admission_date or r.date
			if not when:
				continue
			when = getdate(when)
			period = (when.year, when.month)
		else:
			month_num = MONTH_NUMBER.get(r.month)
			if not month_num:
				continue
			if cursor:
				period = _next_period(cursor, month_num)
				# Move the cursor past this month so a repeated month name
				# (13-month academic years) lands in the following year.
				cursor = (period[0] + 1, 1) if period[1] == 12 else (period[0], period[1] + 1)
			elif r.date:
				period = (getdate(r.date).year, month_num)
			elif r.admission_date:
				period = _next_period((getdate(r.admission_date).year, getdate(r.admission_date).month), month_num)
			else:
				continue

		paid = flt(r.amount_paid)
		if r.status in PAID_STATUSES:
			pending = 0.0
		elif r.status in PENDING_STATUSES:
			if r.student_status != "Active":
				continue
			if not is_starting and (cint(r.yearly_fees_student) or cint(r.scholarship_student)):
				continue
			if r.status != "Not Paid" and flt(r.pending) > 0:
				pending = flt(r.pending)
			elif is_starting:
				expected = flt(r.amount_need_to_pay) or flt(r.starting_payment)
				pending = flt(r.pending) if flt(r.pending) > 0 else max(expected - paid, 0.0)
			else:
				pending = max(flt(r.monthly_fee) - paid, 0.0)
			if not pending and not paid:
				continue
		else:
			continue

		entries.append(
			frappe._dict(
				section="starting" if is_starting else "monthly",
				year=period[0],
				month=period[1],
				is_paid=r.status in PAID_STATUSES,
				paid=paid,
				pending=pending,
				student=r.student,
				student_name=r.student_name,
				standard=r.standard,
				batch=r.current_batch,
				status=r.status,
			)
		)
	return entries


def _filter(entries, year, month):
	"""Entries in the selected year / month.

	The starting payment is a one-time fee that covers the whole academic
	year, so the Month filter does not apply to it; only the Year does.
	"""
	year, month = cint(year), cint(month)
	return [
		e
		for e in entries
		if (not year or e.year == year)
		and (not month or e.section == "starting" or e.month == month)
	]


def _empty_block():
	return {
		"total_amount": 0.0, "total_count": 0,
		"paid_amount": 0.0, "paid_count": 0,
		"pending_amount": 0.0, "not_paid_count": 0,
	}


def _add(block, e):
	block["total_amount"] += e.paid + e.pending
	block["total_count"] += 1
	block["paid_amount"] += e.paid
	if e.is_paid:
		block["paid_count"] += 1
	else:
		block["pending_amount"] += e.pending
		block["not_paid_count"] += 1


@frappe.whitelist()
def get_summary(year=None, month=None):
	_guard()
	entries = _entries()

	data = {s: _empty_block() for s in SECTIONS}
	for e in _filter(entries, year, month):
		_add(data[e.section], e)
		_add(data["overall"], e)

	years = {e.year for e in entries} | {getdate(nowdate()).year}
	return {"data": data, "years": sorted(years, reverse=True)}


@frappe.whitelist()
def get_breakdown(section, kind, year=None, month=None):
	"""Student-wise rows behind one card."""
	_guard()
	if section not in SECTIONS or kind not in KINDS:
		frappe.throw(_("Invalid card."))

	rows = []
	for e in _filter(_entries(), year, month):
		if section != "overall" and e.section != section:
			continue
		if kind == "paid" and not e.is_paid:
			continue
		if kind == "pending" and e.is_paid:
			continue
		rows.append(
			{
				"student": e.student,
				"student_name": e.student_name,
				"standard": e.standard,
				"batch": e.batch,
				"fee": _("Starting Payment") if e.section == "starting" else _(MONTH_NAMES[e.month - 1]),
				"period": f"{MONTH_NAMES[e.month - 1][:3]} {e.year}",
				"status": e.status,
				"paid": e.paid,
				"pending": e.pending,
			}
		)
	rows.sort(key=lambda r: (-r["pending"], r["student_name"] or ""))
	return rows
