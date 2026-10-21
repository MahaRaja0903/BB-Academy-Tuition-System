"""Student Count Report: the data layer.

The "Actual Students Count List — STD wise & Month wise" sheet, in three
sections like the printed original:

  • 6th To 9th Std      one row per standard and gender, May to April
  • 10th To 12th Girls  one row per standard and group, April to March
  • 10th To 12th Boys   the same rows for boys

A student counts in a month when they were on the roll at any time in that
month: admitted on or before its last day, and not discontinued or suspended
before its first day. Students who rejoined are counted for each period they
were on the roll, read from their Student Rejoin Logs. Months after today are
left blank, not 0.

Students are counted under their current standard and group.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_months, get_last_day, getdate, today

# Mirrors the roles on student_count_report.json. Whitelisted methods can be
# called without opening the page, so they need their own check.
ALLOWED_ROLES = {
	"System Manager",
	"Administrator",
	"Receptionist",
	"Accountant",
	"Teacher",
}

GENDERS = ("Girls", "Boys")

# Short names the sheet uses for 11th/12th groups.
GROUP_ABBR = {
	"Business Maths": "BM",
	"Computer Application": "CA",
	"Biology": "BIO",
	"Computer Science": "CS",
}

# Rows of the 10th–12th sections in the sheet's order, as
# (academic_order, stream, group). Any other combination found among the
# students is added after these, so no one is left out of the totals.
HIGHER_ROWS = [
	(10, None, None),
	(11, "Commerce", "Business Maths"),
	(11, "Commerce", "Computer Application"),
	(11, "Science", "Biology"),
	(11, "Science", "Computer Science"),
	(12, "Commerce", "Business Maths"),
	(12, "Commerce", "Computer Application"),
	(12, "Science", "Biology"),
	(12, "Science", "Computer Science"),
	(11, "Commerce", "Statistics"),
	(12, "Commerce", "Statistics"),
]


def _guard():
	if frappe.session.user == "Administrator":
		return
	if not (ALLOWED_ROLES & set(frappe.get_roles())):
		frappe.throw(_("You are not permitted to view this report."), frappe.PermissionError)


def _months(first):
	"""Twelve month starts from `first`."""
	return [getdate(add_months(first, i)) for i in range(12)]


def _periods(student, rejoins):
	"""(start, end) spans the student was on the roll; end is None while ongoing."""
	periods = []
	start = getdate(student.admission_date) if student.admission_date else None
	for log in rejoins:
		periods.append((start, getdate(log.discontinued_date) if log.discontinued_date else None))
		start = getdate(log.rejoined_date) if log.rejoined_date else None

	end = None
	if student.status == "Discontinued" and student.discontinued__date:
		end = getdate(student.discontinued__date)
	elif student.status == "Suspended" and student.suspended_date:
		end = getdate(student.suspended_date)
	periods.append((start, end))
	return [p for p in periods if p[0]]


def _on_roll(periods, month_start):
	month_end = getdate(get_last_day(month_start))
	return any(start <= month_end and (end is None or end >= month_start) for start, end in periods)


def _higher_label(order, stream, group):
	if order == 10:
		return "10th STD"
	if group == "Statistics":
		return f"{order}th STATISTICS"
	stream = (stream or "").upper()
	group = GROUP_ABBR.get(group) or group or _("Group not set")
	return f"{order}th {stream} ({group})"


def _section(title, months, row_keys, labels, students_by_row, upto):
	rows = []
	totals = [0 if m <= upto else None for m in months]
	for key in row_keys:
		counts = []
		for i, m in enumerate(months):
			if m > upto:
				counts.append(None)
				continue
			n = sum(1 for p in students_by_row.get(key, []) if _on_roll(p, m))
			counts.append(n)
			totals[i] += n
		rows.append({
			"label": labels[key],
			"counts": counts,
			"highest": max((c for c in counts if c is not None), default=None),
		})
	return {
		"title": title,
		"months": [m.strftime("%b").upper() for m in months],
		"rows": rows,
		"totals": totals,
		"highest": max((t for t in totals if t is not None), default=None),
	}


@frappe.whitelist()
def get_report(academic_year):
	_guard()

	ay = frappe.db.get_value("Academic Year", academic_year, ["name", "start_date"], as_dict=True)
	if not ay or not ay.start_date:
		frappe.throw(_("Academic Year {0} has no Start Date.").format(academic_year))

	# The sheet's years run April to March (10th–12th) and May to April (6th–9th).
	april = getdate(f"{getdate(ay.start_date).year}-04-01")
	upto = getdate(today())

	standards = {
		s.name: s
		for s in frappe.get_all("Standard", fields=["name", "group", "academic_order"])
	}

	rejoins = defaultdict(list)
	for log in frappe.get_all(
		"Student Rejoin Log",
		fields=["student", "discontinued_date", "rejoined_date"],
		order_by="rejoined_date asc",
	):
		rejoins[log.student].append(log)

	students = frappe.get_all(
		"Student",
		filters={"admission_date": ["<=", get_last_day(add_months(april, 12))]},
		fields=["name", "standard", "group", "gender", "status", "admission_date",
			"discontinued__date", "suspended_date"],
	)

	lower_rows = defaultdict(list)  # (order, std label, gender) -> [periods]
	higher_rows = {g: defaultdict(list) for g in GENDERS}  # gender -> (order, stream, group) -> [periods]
	for s in students:
		std = standards.get(s.standard)
		if not std or s.gender not in GENDERS:
			continue
		periods = _periods(s, rejoins.get(s.name, []))
		order = std.academic_order or 0
		if order <= 9:
			lower_rows[(order, std.name, s.gender)].append(periods)
		elif order == 10:
			higher_rows[s.gender][(10, None, None)].append(periods)
		else:
			higher_rows[s.gender][(order, std.group, s.group or None)].append(periods)

	# 6th–9th: every active standard below 10th gets a Girls and a Boys row.
	lower_keys = set(lower_rows)
	for std in standards.values():
		if std.academic_order and std.academic_order <= 9:
			for g in GENDERS:
				lower_keys.add((std.academic_order, std.name, g))
	lower_keys = sorted(lower_keys, key=lambda k: (k[0], k[1], GENDERS.index(k[2])))
	lower_labels = {k: f"{k[0]}th STD - {k[2]}" if k[0] else f"{k[1]} - {k[2]}" for k in lower_keys}

	sections = [
		_section(_("6th To 9th Std"), _months(add_months(april, 1)),
			lower_keys, lower_labels, lower_rows, upto),
	]
	for g in GENDERS:
		extra = sorted(
			(k for k in higher_rows[g] if k not in HIGHER_ROWS),
			key=lambda k: (k[0], k[1] or "", k[2] or "~"),
		)
		keys = HIGHER_ROWS + extra
		labels = {k: _higher_label(*k) for k in keys}
		sections.append(
			_section(_("10th To 12th Std - {0}").format(_(g)), _months(april),
				keys, labels, higher_rows[g], upto)
		)

	return {
		"academic_year": ay.name,
		"year_label": f"{april.year} - {april.year + 1}",
		"sections": sections,
	}
