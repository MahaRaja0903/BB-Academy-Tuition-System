"""BB Academy dashboard — data layer.

Money notes (important, and the reason every figure below comes from the
Student's own `payment_details` rows rather than from Fee Invoice):

* Fee Invoice only covers what has been raised inside this system. The academy
  ran for years before that, and those older fees were recorded straight onto
  the student — so the invoice table holds a handful of rows against thousands
  of real payments. Reading it reports a fraction of the money and dates the
  history to whenever the system was adopted.
* `Student Payment Detail` is the ledger the rest of the app maintains:
  `FeeInvoice.update_student_payment_detail()` writes every submitted invoice
  into it, and the older history is already there. It is the one table that
  holds both.
* It also carries a real payment date (`date`), so collections are dated by
  when the money actually came in rather than by an invoice date.

Outstanding is derived the same way `update_student_totals()` and the Pending
Balance Break Down report derive it, so the three agree: what the month was
billed (`amount_need_to_pay`) less what came in (`amount_paid`), and nothing at
all for a month that is settled or was never owed. Amounts are only ever read
from the table — never inferred from the student's standing fee — because some
students are on free education and their months carry no amount by design.

The stored `Fee Invoice.status` field is still never trusted anywhere: 
`FeeInvoice.update_status()` is commented out in the controller, so a submitted
invoice keeps `status = "Draft"` forever.
"""

import frappe
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, nowdate

from bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice import SETTLED_STATUSES

# Roles allowed to read dashboard figures. Mirrors the roles on bb_dashboard.json —
# the whitelisted endpoints are callable independently of page access, so they
# need their own guard.
ALLOWED_ROLES = {
	"System Manager",
	"Administrator",
	"Receptionist",
	"Accountant",
	"Teacher",
}

# A month that is settled, or was never owed in the first place, has nothing
# outstanding whatever its amounts say -- a month covered by the starting
# payment carries no amount_paid of its own, and a No Fees month is free.
NOTHING_OWED_STATUSES = SETTLED_STATUSES + ("No Fees",)

# The fee ledger every money figure reads from.
LEDGER_SQL = """
	from `tabStudent Payment Detail` spd
	inner join `tabStudent` s on s.name = spd.parent
	where spd.parenttype = 'Student'
"""

BILLED_SQL = "coalesce(spd.amount_need_to_pay, 0)"
COLLECTED_SQL = "coalesce(spd.amount_paid, 0)"

# Only ever the amounts the table itself records -- never the student's standing
# monthly fee, which would bill the free-education students for months they were
# deliberately given.
OUTSTANDING_SQL = f"""
	case
		when ifnull(spd.status, '') in %(nothing_owed)s then 0
		else greatest({BILLED_SQL} - {COLLECTED_SQL}, 0)
	end
"""

# Rows that stand for a real fee -- the ones worth counting as "months billed".
REAL_FEE_SQL = "ifnull(spd.status, '') not in ('Not Joined', 'No Fees')"

# The three buckets the status card shows, mapped from the ledger's own statuses.
STATUS_BUCKET_SQL = """
	case
		when ifnull(spd.status, '') in ('Paid', 'Paid By Starting Payment') then 'Paid'
		when ifnull(spd.status, '') = 'Partial' then 'Partially Paid'
		when ifnull(spd.status, '') = 'Reserved' then 'Reserved'
		else 'Unpaid'
	end
"""


# Roles that see every figure, whatever the restrictions below say.
# "Owner" is not a stock Frappe role; it is honoured here in case one is created.
FULL_ACCESS_ROLES = {"System Manager", "Administrator", "Owner"}

# Roles kept away from monthly revenue aggregates and the Reports section.
FINANCE_RESTRICTED_ROLES = {"Receptionist"}


def _guard():
	if frappe.session.user == "Administrator":
		return
	if not (ALLOWED_ROLES & set(frappe.get_roles())):
		frappe.throw(
			frappe._("You are not permitted to view the BB Academy dashboard."),
			frappe.PermissionError,
		)


def _can_view_finance():
	"""Whether this session may see monthly collection totals and Reports.

	Full access wins over restriction, so someone holding both System Manager
	and Receptionist is NOT restricted.

	This is enforced here, in the data layer — the page also hides the matching
	UI, but that is cosmetic. Every whitelisted endpoint below is callable
	directly, so the figures have to be withheld at the source.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = set(frappe.get_roles())
	if roles & FULL_ACCESS_ROLES:
		return True
	return not (roles & FINANCE_RESTRICTED_ROLES)


def _require_finance():
	if not _can_view_finance():
		frappe.throw(
			frappe._("You are not permitted to view collection totals."),
			frappe.PermissionError,
		)


# Monthly aggregates withheld from restricted roles. Today's collection,
# outstanding balances and the overall collected/billed ratio are NOT in this
# list — a receptionist still needs those to take and chase payments.
FINANCE_ONLY_KPIS = ("monthly_collection", "last_month_collection", "billed_this_month")


# ─────────────────────────────────────────────────────────────────────────────
# Single batched endpoint — the page makes exactly one call.
# ─────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_dashboard():
	"""Everything the dashboard page renders, in one round-trip."""
	_guard()

	today = nowdate()
	month_start = get_first_day(today)
	month_end = get_last_day(today)

	can_finance = _can_view_finance()

	kpi = _get_kpis(today, month_start, month_end)
	if not can_finance:
		for field in FINANCE_ONLY_KPIS:
			kpi.pop(field, None)

	return {
		"meta": {
			"today": today,
			"month_label": getdate(today).strftime("%B %Y"),
			"currency": frappe.db.get_default("currency") or "INR",
			"has_data": _has_any_data(),
			"permissions": {
				"finance_summary": can_finance,
				"reports": can_finance,
			},
		},
		"kpi": kpi,
		"counts": get_setup_counts(),
		"collection_trend": get_collection_trend() if can_finance else [],
		"invoice_status": get_invoice_status_breakdown(),
		"students_by_standard": get_students_by_standard(),
		"enquiry_sources": get_enquiry_sources(),
		"recent_payments": get_recent_collections(),
		"birthdays": get_todays_birthdays(),
		"followups": get_pending_followups(),
		"outstanding_invoices": get_outstanding_invoices(),
	}


@frappe.whitelist()
def get_setup_counts():
	"""Record counts for the master doctypes surfaced in Quick Actions.

	`School` and `Batch` carry an `is_active` check, so both the active count
	(shown on the tile) and the total (shown in its tooltip) are returned.
	`Student Batch Transition` is submittable — only submitted rows count.
	"""
	_guard()
	return {
		"schools": frappe.db.count("School", {"is_active": 1}),
		"schools_total": frappe.db.count("School"),
		"batches": frappe.db.count("Batch", {"is_active": 1}),
		"batches_total": frappe.db.count("Batch"),
		"batch_transitions": frappe.db.count("Student Batch Transition", {"docstatus": 1}),
		"standards": frappe.db.count("Standard"),
	}


def _has_any_data():
	"""True once the site has real records, so the page can show onboarding
	instead of a wall of zeros on a fresh install."""
	for doctype in ("Student", "Student Enquiry Form", "Fee Invoice"):
		if frappe.db.count(doctype):
			return True
	return False


def _sum_payments(start, end=None):
	"""Collections between two dates (inclusive), or on a single date.

	Dated by `Student Payment Detail.date` — the day the money was actually
	taken, not the day an invoice happened to be raised.
	"""
	if end is None:
		end = start
	return flt(
		frappe.db.sql(
			f"""
			select sum({COLLECTED_SQL})
			{LEDGER_SQL}
				and spd.date between %(start)s and %(end)s
			""",
			{"start": start, "end": end},
		)[0][0]
		or 0,
		2,
	)


def _get_kpis(today, month_start, month_end):
	active_students = frappe.db.count("Student", {"status": "Active"})
	discontinued_students = frappe.db.count("Student", {"status": "Discontinued"})
	suspended_students = frappe.db.count("Student", {"status": "Suspended"})
	total_students = frappe.db.count("Student")

	new_admissions = frappe.db.count(
		"Student Admission Form",
		{"docstatus": 1, "application_date": ["between", [month_start, month_end]]},
	)

	# Student Enquiry Form is not submittable, so no docstatus filter.
	# status options are: Open | Converted | Lost | Follow-up
	open_enquiries = frappe.db.count(
		"Student Enquiry Form", {"status": ["in", ["Open", "Follow-up"]]}
	)

	# Receivables across the whole fee ledger, older history included.
	receivables = frappe.db.sql(
		f"""
		select
			sum(case when {REAL_FEE_SQL} then 1 else 0 end) as fee_months,
			sum(case when {OUTSTANDING_SQL} > 0 then 1 else 0 end) as unpaid_count,
			sum({OUTSTANDING_SQL}) as outstanding,
			sum({BILLED_SQL}) as billed,
			sum({COLLECTED_SQL}) as paid
		{LEDGER_SQL}
		""",
		{"nothing_owed": NOTHING_OWED_STATUSES},
		as_dict=True,
	)[0]

	# The ledger is keyed by month name, not by a billing date, so "billed this
	# month" is what this calendar month's row asks for across every student.
	billed_this_month = flt(
		frappe.db.sql(
			f"""
			select sum({BILLED_SQL})
			{LEDGER_SQL}
				and spd.month = %(month)s
			""",
			{"month": getdate(today).strftime("%B")},
		)[0][0]
		or 0,
		2,
	)

	todays_collections = _sum_payments(today)
	monthly_collection = _sum_payments(month_start, month_end)
	last_month_collection = _sum_payments(
		get_first_day(add_months(today, -1)), get_last_day(add_months(today, -1))
	)

	total_billed = flt(receivables.billed or 0, 2)
	total_paid = flt(receivables.paid or 0, 2)

	return {
		"active_students": active_students,
		"discontinued_students": discontinued_students,
		"suspended_students": suspended_students,
		"total_students": total_students,
		"new_admissions": new_admissions,
		"open_enquiries": open_enquiries,
		"unpaid_invoices": int(receivables.unpaid_count or 0),
		"total_invoices": int(receivables.fee_months or 0),
		"total_pending": flt(receivables.outstanding or 0, 2),
		"total_billed": total_billed,
		"total_collected": total_paid,
		"collection_rate": flt(total_paid / total_billed * 100, 1) if total_billed else 0.0,
		"billed_this_month": billed_this_month,
		"todays_collections": todays_collections,
		"monthly_collection": monthly_collection,
		"last_month_collection": last_month_collection,
	}


# ─────────────────────────────────────────────────────────────────────────────
# Sections (kept individually whitelisted so they stay usable on their own)
# ─────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_collection_trend(months=12):
	"""Monthly collection totals for the trailing `months` months.

	One GROUP BY, not one query per month.
	"""
	_guard()
	_require_finance()
	months = int(months)
	today = getdate(nowdate())
	start = get_first_day(add_months(today, -(months - 1)))
	end = get_last_day(today)

	rows = frappe.db.sql(
		f"""
		select date_format(spd.date, '%%Y-%%m') as ym,
		       sum({COLLECTED_SQL}) as amount
		{LEDGER_SQL}
			and spd.date between %(start)s and %(end)s
		group by ym
		""",
		{"start": start, "end": end},
		as_dict=True,
	)
	totals = {r.ym: flt(r.amount, 2) for r in rows}

	# Emit every month in range, including the empty ones, so the axis is continuous.
	out = []
	for i in range(months - 1, -1, -1):
		d = getdate(get_first_day(add_months(today, -i)))
		out.append(
			{
				"month": d.strftime("%b %y"),
				"amount": totals.get(d.strftime("%Y-%m"), 0.0),
			}
		)
	return out


@frappe.whitelist()
def get_invoice_status_breakdown():
	"""Fee months grouped by where they stand, with amounts.

	Counted per month owed rather than per invoice, because the older history
	has no invoice behind it. Months the student never owed -- before they
	joined, or given free -- are left out entirely.
	"""
	_guard()
	# The bucket must be aliased inside a subquery: grouping on the alias
	# directly would bind to `spd.status` instead and split the buckets back
	# into the raw statuses.
	rows = frappe.db.sql(
		f"""
		select derived.status as status,
		       count(*) as count,
		       sum(derived.billed) as billed,
		       sum(derived.outstanding) as outstanding
		from (
			select
				{STATUS_BUCKET_SQL} as status,
				{BILLED_SQL} as billed,
				{OUTSTANDING_SQL} as outstanding
			{LEDGER_SQL}
				and {REAL_FEE_SQL}
		) as derived
		group by derived.status
		""",
		{"nothing_owed": NOTHING_OWED_STATUSES},
		as_dict=True,
	)

	# Fixed order so colours never shift as counts change.
	order = {"Paid": 0, "Partially Paid": 1, "Reserved": 2, "Unpaid": 3}
	rows.sort(key=lambda r: order.get(r.status, 99))
	for r in rows:
		r["billed"] = flt(r.billed, 2)
		r["outstanding"] = flt(r.outstanding, 2)
	return rows


@frappe.whitelist()
def get_students_by_standard():
	"""Active student count per standard, highest first."""
	_guard()
	# Subquery for the same reason as get_invoice_status_breakdown: `group by
	# standard` would bind to the raw column, so NULL and '' would form two
	# separate groups that both render as "Unassigned".
	return frappe.db.sql(
		"""
		select derived.standard as standard, count(*) as count
		from (
			select coalesce(nullif(standard, ''), 'Unassigned') as standard
			from `tabStudent`
			where status = 'Active'
		) as derived
		group by derived.standard
		order by count desc, standard asc
		""",
		as_dict=True,
	)


@frappe.whitelist()
def get_enquiry_sources():
	"""Enquiry count grouped by source channel."""
	_guard()
	return frappe.db.sql(
		"""
		select derived.source as source,
		       count(*) as count,
		       sum(derived.is_open) as open_count,
		       sum(derived.is_converted) as converted
		from (
			select
				coalesce(nullif(source, ''), 'Not specified') as source,
				case when status in ('Open', 'Follow-up') then 1 else 0 end as is_open,
				case when status = 'Converted' then 1 else 0 end as is_converted
			from `tabStudent Enquiry Form`
		) as derived
		group by derived.source
		order by count desc, source asc
		""",
		as_dict=True,
	)


@frappe.whitelist()
def get_recent_collections(limit=8):
	"""The payments most recently taken, newest first.

	One row per month settled, dated by when the money came in.
	"""
	_guard()
	return frappe.db.sql(
		f"""
		select
			spd.parent as student,
			s.student_name,
			s.standard,
			spd.month,
			spd.date as paid_on,
			{COLLECTED_SQL} as paid_amount,
			{OUTSTANDING_SQL} as outstanding
		{LEDGER_SQL}
			and spd.date is not null
			and {COLLECTED_SQL} > 0
		order by spd.date desc, spd.modified desc
		limit %(limit)s
		""",
		{"nothing_owed": NOTHING_OWED_STATUSES, "limit": int(limit)},
		as_dict=True,
	)


@frappe.whitelist()
def get_todays_birthdays():
	"""Active students whose birthday falls today or tomorrow."""
	_guard()
	today = getdate(nowdate())
	tomorrow = add_days(today, 1)
	return frappe.db.sql(
		"""
		select name, student_name, date_of_birth, standard, current_batch,
		       if(month(date_of_birth) = %s and day(date_of_birth) = %s, 'Today', 'Tomorrow') as day_label
		from `tabStudent`
		where status = 'Active'
		  and date_of_birth is not null
		  and (
			(month(date_of_birth) = %s and day(date_of_birth) = %s) or
			(month(date_of_birth) = %s and day(date_of_birth) = %s)
		  )
		order by day_label asc, student_name asc
		""",
		(today.month, today.day, today.month, today.day, tomorrow.month, tomorrow.day),
		as_dict=True,
	)


@frappe.whitelist()
def get_pending_followups(limit=8):
	"""Open enquiries whose follow-up date is today or already past."""
	_guard()
	today = nowdate()
	rows = frappe.db.get_all(
		"Student Enquiry Form",
		filters={
			"status": ["in", ["Open", "Follow-up"]],
			"next_follow_up_date": ["<=", today],
		},
		fields=[
			"name",
			"applicant_name",
			"father_name",
			"mother_name",
			"father_number",
			"mother_number",
			"next_follow_up_date",
			"standard",
		],
		order_by="next_follow_up_date asc",
		limit=int(limit),
	)
	today_date = getdate(today)
	for r in rows:
		r["overdue_days"] = (today_date - getdate(r.next_follow_up_date)).days
		r["parent_name"] = r.father_name or r.mother_name
		r["parent_mobile"] = r.father_number or r.mother_number
	return rows


@frappe.whitelist()
def get_outstanding_invoices(limit=8):
	"""Students still carrying a balance, biggest first.

	Grouped by student rather than by invoice: the older fees have no invoice
	behind them, and what the office needs is who to chase and for which
	months. There is no due date anywhere in the schema, so these are
	outstanding rather than overdue -- the months name themselves instead.
	"""
	_guard()
	rows = frappe.db.sql(
		f"""
		select
			spd.parent as student,
			s.student_name,
			s.standard,
			s.current_batch as batch,
			sum({OUTSTANDING_SQL}) as outstanding,
			sum(case when {OUTSTANDING_SQL} > 0 then 1 else 0 end) as months_due,
			sum({COLLECTED_SQL}) as paid_amount,
			group_concat(
				case when {OUTSTANDING_SQL} > 0 then spd.month end
				order by spd.idx separator ', '
			) as months
		{LEDGER_SQL}
			and s.status = 'Active'
		group by spd.parent, s.student_name, s.standard, s.current_batch
		having outstanding > 0
		order by outstanding desc
		limit %(limit)s
		""",
		{"nothing_owed": NOTHING_OWED_STATUSES, "limit": int(limit)},
		as_dict=True,
	)

	for r in rows:
		r["outstanding"] = flt(r.outstanding, 2)
		r["months_due"] = int(r.months_due or 0)

	return rows


# ─────────────────────────────────────────────────────────────────────────────
# Backwards compatibility
# ─────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_dashboard_data():
	"""Legacy KPI-only endpoint. Superseded by `get_dashboard`."""
	_guard()
	today = nowdate()
	kpi = _get_kpis(today, get_first_day(today), get_last_day(today))
	if not _can_view_finance():
		for field in FINANCE_ONLY_KPIS:
			kpi.pop(field, None)
	return kpi


@frappe.whitelist()
def get_overdue_invoices(limit=8):
	"""Deprecated alias for `get_outstanding_invoices`."""
	return get_outstanding_invoices(limit=limit)


@frappe.whitelist()
def get_recent_payments(limit=8):
	"""Deprecated alias for `get_recent_collections`."""
	return get_recent_collections(limit=limit)
