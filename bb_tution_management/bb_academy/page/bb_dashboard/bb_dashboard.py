"""BB Academy dashboard — data layer.

Money notes (important, and the reason this file does not filter on
`Fee Invoice.status`):

* `FeeInvoice.update_status()` is commented out in the controller, and the
  `status` field defaults to "Draft". A submitted invoice that has never
  received a payment therefore keeps `status = "Draft"` forever — filtering on
  `status in ("Unpaid", "Partially Paid")` silently misses every one of them.
* `FeeInvoice.calculate_outstanding()` writes `balance_amount` but never
  assigns `outstanding_amount`; that field is only maintained by
  `FeesPaymentEntry.update_invoice_status()`. So `outstanding_amount` is NULL/0
  on a fresh invoice, and `sum(outstanding_amount)` under-reports badly.

So everything below derives both the status and the outstanding balance from
`grand_total - paid_amount`, which the controllers do keep correct. The stored
`status` field is never trusted.

Collections come from `Fee Invoice.paid_amount`, NOT from `Fees Payment Entry`.
The team records payments on the invoice itself — `fee_invoice.js` rolls the
`fees_details` rows up into `paid_amount`, and nothing creates a Payment Entry
(hence the "Payment Entry is removed" comment in the Fee Invoice controller).
Reading the Payment Entry table would report zero forever.

Using the invoice figure is also the safe choice if Payment Entries do get used
again: `FeesPaymentEntry.update_invoice_status()` *adds* its amount into
`invoice.paid_amount`, so the invoice column is the single accumulator both
paths write to. Summing both tables would double-count.

Caveat worth knowing: Fee Invoice carries only `invoice_date` — there is no
payment date anywhere in the schema — so collections are dated by the invoice.
A payment added later to an older invoice counts on that invoice's date. If you
ever need true payment dating, the schema needs a date field first.
"""

import frappe
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate, nowdate

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

# Derived outstanding balance for a submitted invoice.
OUTSTANDING_SQL = "greatest(coalesce(grand_total, 0) - coalesce(paid_amount, 0), 0)"

# Derived status, ignoring the unreliable stored `status` field.
STATUS_SQL = f"""
	case
		when {OUTSTANDING_SQL} <= 0 then 'Paid'
		when coalesce(paid_amount, 0) > 0 then 'Partially Paid'
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

	Sums `Fee Invoice.paid_amount` dated by `invoice_date` — see module docstring
	for why this is the invoice column and not `Fees Payment Entry.amount`.
	"""
	if end is None:
		end = start
	return flt(
		frappe.db.sql(
			"""
			select sum(coalesce(paid_amount, 0)) from `tabFee Invoice`
			where docstatus = 1 and invoice_date between %s and %s
			""",
			(start, end),
		)[0][0]
		or 0,
		2,
	)


def _get_kpis(today, month_start, month_end):
	active_students = frappe.db.count("Student", {"status": "Active"})
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

	# Receivables, derived rather than read from `status`/`outstanding_amount`.
	receivables = frappe.db.sql(
		f"""
		select
			count(*) as invoices,
			sum(case when {OUTSTANDING_SQL} > 0 then 1 else 0 end) as unpaid_count,
			sum({OUTSTANDING_SQL}) as outstanding,
			sum(coalesce(grand_total, 0)) as billed,
			sum(coalesce(paid_amount, 0)) as paid
		from `tabFee Invoice`
		where docstatus = 1
		""",
		as_dict=True,
	)[0]

	billed_this_month = flt(
		frappe.db.sql(
			"""
			select sum(coalesce(grand_total, 0)) from `tabFee Invoice`
			where docstatus = 1 and invoice_date between %s and %s
			""",
			(month_start, month_end),
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
		"total_students": total_students,
		"new_admissions": new_admissions,
		"open_enquiries": open_enquiries,
		"unpaid_invoices": int(receivables.unpaid_count or 0),
		"total_invoices": int(receivables.invoices or 0),
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
		"""
		select date_format(invoice_date, '%%Y-%%m') as ym,
		       sum(coalesce(paid_amount, 0)) as amount
		from `tabFee Invoice`
		where docstatus = 1 and invoice_date between %s and %s
		group by ym
		""",
		(start, end),
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
	"""Submitted invoices grouped by *derived* status, with amounts."""
	_guard()
	# The derived column must be aliased inside a subquery: `Fee Invoice` has a
	# real `status` column, and MariaDB resolves `group by status` to that column
	# rather than to the select alias — which silently collapses every invoice
	# into one "Draft" bucket.
	rows = frappe.db.sql(
		f"""
		select derived.status as status,
		       count(*) as count,
		       sum(derived.billed) as billed,
		       sum(derived.outstanding) as outstanding
		from (
			select
				{STATUS_SQL} as status,
				coalesce(grand_total, 0) as billed,
				{OUTSTANDING_SQL} as outstanding
			from `tabFee Invoice`
			where docstatus = 1
		) as derived
		group by derived.status
		""",
		as_dict=True,
	)

	# Fixed order so colours never shift as counts change.
	order = {"Paid": 0, "Partially Paid": 1, "Unpaid": 2}
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
	"""Most recently paid invoices — money actually taken in."""
	_guard()
	return frappe.db.sql(
		f"""
		select
			name, student, student_name, invoice_date,
			coalesce(paid_amount, 0) as paid_amount,
			coalesce(grand_total, 0) as grand_total,
			{OUTSTANDING_SQL} as outstanding
		from `tabFee Invoice`
		where docstatus = 1 and coalesce(paid_amount, 0) > 0
		order by invoice_date desc, modified desc
		limit %s
		""",
		(int(limit),),
		as_dict=True,
	)


@frappe.whitelist()
def get_todays_birthdays():
	"""Active students whose birthday falls today (month + day match in SQL)."""
	_guard()
	today = getdate(nowdate())
	return frappe.db.sql(
		"""
		select name, student_name, date_of_birth, standard, current_batch
		from `tabStudent`
		where status = 'Active'
		  and date_of_birth is not null
		  and month(date_of_birth) = %s
		  and day(date_of_birth) = %s
		order by student_name asc
		""",
		(today.month, today.day),
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
			"parent_name",
			"parent_mobile",
			"next_follow_up_date",
			"standard",
		],
		order_by="next_follow_up_date asc",
		limit=int(limit),
	)
	today_date = getdate(today)
	for r in rows:
		r["overdue_days"] = (today_date - getdate(r.next_follow_up_date)).days
	return rows


@frappe.whitelist()
def get_outstanding_invoices(limit=8):
	"""Submitted invoices still carrying a balance, oldest first.

	Named "outstanding" rather than "overdue" on purpose: Fee Invoice has no
	due-date field, so there is nothing to be past. `age_days` is days since
	the invoice date, which is what the UI labels.
	"""
	_guard()
	return frappe.db.sql(
		f"""
		select
			name, student, student_name, invoice_date,
			coalesce(grand_total, 0) as grand_total,
			coalesce(paid_amount, 0) as paid_amount,
			{OUTSTANDING_SQL} as outstanding,
			datediff(%s, invoice_date) as age_days
		from `tabFee Invoice`
		where docstatus = 1 and {OUTSTANDING_SQL} > 0
		order by invoice_date asc
		limit %s
		""",
		(nowdate(), int(limit)),
		as_dict=True,
	)


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
	"""Deprecated alias for `get_recent_collections`.

	The old implementation listed `Fees Payment Entry` records, which this
	install does not create.
	"""
	return get_recent_collections(limit=limit)
