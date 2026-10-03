"""Admission Trends dashboard: the data layer.

An admission is a Student record, dated by its `admission_date`. That covers
students who came through a Student Admission Form (which copies its
application date across) and students entered straight into the Student list.
Students who later discontinued or were suspended still count as admissions in
the month they joined, unless the Status filter narrows to Active.

Enquiries (Student Enquiry Form, by `enquiry_date`) are returned month by month
alongside, under the same standard and gender filters, so the owner can see
demand next to joins. They are not linked one-to-one to admissions.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_months, getdate

# Mirrors the roles on admission_trends.json. Whitelisted methods can be
# called without opening the page, so they need their own check.
ALLOWED_ROLES = {
	"System Manager",
	"Administrator",
	"Receptionist",
	"Accountant",
	"Teacher",
}

GENDERS = ("Girls", "Boys")
STATUSES = ("All", "Active")

# A range longer than this is almost certainly a typo in a year field.
MAX_MONTHS = 60


def _guard():
	if frappe.session.user == "Administrator":
		return
	if not (ALLOWED_ROLES & set(frappe.get_roles())):
		frappe.throw(_("You are not permitted to view this dashboard."), frappe.PermissionError)


def _parse_standards(standards):
	if not standards:
		return []
	if isinstance(standards, str):
		try:
			standards = json.loads(standards)
		except ValueError:
			standards = [s.strip() for s in standards.split(",")]
	return [s for s in standards if s]


def _month_keys(start, end):
	"""'YYYY-MM' for every month from start to end, both included."""
	keys = []
	cur = getdate(start).replace(day=1)
	end = getdate(end).replace(day=1)
	while cur <= end and len(keys) < MAX_MONTHS:
		keys.append(cur.strftime("%Y-%m"))
		cur = getdate(add_months(cur, 1))
	return keys


@frappe.whitelist()
def get_trends(from_date=None, to_date=None, standards=None, gender=None, status="All"):
	"""Admissions per month and standard, with enquiries per month beside them.

	gender:    "Girls" / "Boys" narrows to that gender; anything else is both.
	status:    "All" counts every admitted student, "Active" only those still
	           active today.
	standards: a list, or a JSON list, that narrows both admissions and enquiries.
	"""
	_guard()

	if from_date and to_date and getdate(from_date) > getdate(to_date):
		frappe.throw(_("From Date cannot be after To Date."))
	if gender not in GENDERS:
		gender = None
	if status not in STATUSES:
		status = "All"
	standards = _parse_standards(standards)

	def where(date_col):
		conditions = [f"{date_col} is not null"]
		values = {}
		if from_date:
			conditions.append(f"{date_col} >= %(from_date)s")
			values["from_date"] = getdate(from_date)
		if to_date:
			conditions.append(f"{date_col} <= %(to_date)s")
			values["to_date"] = getdate(to_date)
		if standards:
			conditions.append("x.standard in %(standards)s")
			values["standards"] = tuple(standards)
		if gender:
			conditions.append("x.gender = %(gender)s")
			values["gender"] = gender
		return conditions, values

	conditions, values = where("x.admission_date")
	if status == "Active":
		conditions.append("x.status = 'Active'")
	admissions = frappe.db.sql(
		f"""
		select
			date_format(x.admission_date, '%%Y-%%m') as month,
			x.standard as standard,
			coalesce(st.academic_order, 0) as academic_order,
			x.gender as gender,
			count(*) as count
		from `tabStudent` x
		left join `tabStandard` st on st.name = x.standard
		where {" and ".join(conditions)}
		group by month, x.standard, st.academic_order, x.gender
		""",
		values,
		as_dict=True,
	)

	conditions, values = where("x.enquiry_date")
	enquiries = frappe.db.sql(
		f"""
		select date_format(x.enquiry_date, '%%Y-%%m') as month, count(*) as count
		from `tabStudent Enquiry Form` x
		where {" and ".join(conditions)}
		group by month
		""",
		values,
		as_dict=True,
	)

	# Month axis: the chosen range, or the span of the data when a side is open.
	seen = sorted({r.month for r in admissions} | {r.month for r in enquiries})
	start = getdate(from_date) if from_date else (getdate(seen[0] + "-01") if seen else None)
	end = getdate(to_date) if to_date else (getdate(seen[-1] + "-01") if seen else None)
	months = _month_keys(start, end) if start and end else []
	month_index = {m: i for i, m in enumerate(months)}

	# Standards: every one that had an admission, plus any picked in the filter,
	# in academic order so 6TH sits above 12TH.
	std_order = {}
	for r in admissions:
		std_order[r.standard or ""] = (r.academic_order, r.standard or "")
	for s in standards:
		std_order.setdefault(s, (frappe.db.get_value("Standard", s, "academic_order") or 0, s))
	std_names = sorted(std_order, key=lambda s: std_order[s])

	blank = lambda: [0] * len(months)  # noqa: E731
	by_std = {s: {"standard": s, "months": blank(), "total": 0, "Girls": 0, "Boys": 0} for s in std_names}
	month_totals = blank()
	month_gender = {g: blank() for g in GENDERS}

	for r in admissions:
		i = month_index.get(r.month)
		if i is None:
			continue
		row = by_std[r.standard or ""]
		row["months"][i] += r.count
		row["total"] += r.count
		month_totals[i] += r.count
		if r.gender in GENDERS:
			row[r.gender] += r.count
			month_gender[r.gender][i] += r.count

	month_enquiries = blank()
	for r in enquiries:
		i = month_index.get(r.month)
		if i is not None:
			month_enquiries[i] += r.count

	return {
		"months": months,
		"admissions": month_totals,
		"enquiries": month_enquiries,
		"gender": month_gender,
		"standards": [by_std[s] for s in std_names],
		"total": sum(month_totals),
		"total_enquiries": sum(month_enquiries),
	}
