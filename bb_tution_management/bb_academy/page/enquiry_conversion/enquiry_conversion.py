"""Student Enquiry & Conversion dashboard: the data layer.

*Joined* comes from the Student records, not from the enquiries: a student
counts as joined when their Admission Date (date of joining) falls in the
range. Students admitted before the enquiry form was in use have no enquiry
behind them, so counting "Converted" enquiries would miss them.

*Not joined* is every enquiry in the range that did not convert (Open,
Follow-up and Lost). *Enquired* is joined + not joined, so every joined
student counts as an enquiry whether or not a form was filled in for them,
and conversion never goes above 100%.

Segments are built from the Standard's `academic_order`, not from its name, so
"11TH Science" and "11TH Commerce" both land in the 10th to 12th band.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt, getdate

# Mirrors the roles on enquiry_conversion.json. Whitelisted methods can be
# called without opening the page, so they need their own check.
ALLOWED_ROLES = {
	"System Manager",
	"Administrator",
	"Receptionist",
	"Accountant",
	"Teacher",
}

# (key, label, lowest academic_order, highest academic_order)
BANDS = (
	("6-9", "6th to 9th STD", 6, 9),
	("10-12", "10th to 12th STD", 10, 12),
)

GENDERS = ("Girls", "Boys")


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


def _rate(joined, enquired):
	return round(flt(joined) * 100 / enquired, 1) if enquired else 0.0


# Standard split: how enquiries are grouped by class.
STD_SPLITS = ("Band", "Standard", "None")
# Gender split: Girls and Boys in their own columns, one of them only, or both
# counted together in a single column.
GENDER_SPLITS = ("Split", "Girls", "Boys", "Combined")


def _std_slot(row, std_split, filtered):
	"""(key, label, sort order) of the standard column a row belongs to, or None."""
	if std_split == "Standard":
		if not row.standard:
			return None
		return row.standard, row.standard, (row.academic_order, row.standard)
	if std_split == "None":
		label = _("Selected Standards") if filtered else _("All Standards")
		return "all", label, (0, "")
	for i, (band_key, band_label, low, high) in enumerate(BANDS):
		if low <= (row.academic_order or 0) <= high:
			return band_key, band_label, (i, "")
	return None


def _gender_slots(gender_split):
	if gender_split == "Split":
		return list(GENDERS)
	if gender_split in GENDERS:
		return [gender_split]
	return [None]  # Combined


def _counts(doctype, date_field, from_date, to_date, standards, gender, extra=None):
	"""Row counts of `doctype` per (standard, gender) with `date_field` in range."""
	conditions = ["1=1"]
	values = {}
	if from_date:
		conditions.append(f"e.`{date_field}` >= %(from_date)s")
		values["from_date"] = getdate(from_date)
	if to_date:
		conditions.append(f"e.`{date_field}` <= %(to_date)s")
		values["to_date"] = getdate(to_date)
	if standards:
		conditions.append("e.standard in %(standards)s")
		values["standards"] = standards
	if gender:
		conditions.append("e.gender = %(gender)s")
		values["gender"] = gender
	if extra:
		conditions.append(extra)

	return frappe.db.sql(
		f"""
		select
			e.standard as standard,
			coalesce(st.academic_order, 0) as academic_order,
			e.gender as gender,
			count(*) as count
		from `tab{doctype}` e
		left join `tabStandard` st on st.name = e.standard
		where {" and ".join(conditions)}
		group by e.standard, st.academic_order, e.gender
		""",
		values,
		as_dict=True,
	)


@frappe.whitelist()
def get_conversion(from_date=None, to_date=None, standards=None, std_split="Band", gender_split="Split"):
	"""Enquired / joined / not-joined counts per column for the date range.

	Joined counts Students by Admission Date; not joined counts enquiries that
	did not convert; enquired is the two added together.

	std_split:    "Band" (6th to 9th / 10th to 12th), "Standard" (one per
	              standard) or "None" (all standards in one column).
	gender_split: "Split" (Girls and Boys columns), "Girls" / "Boys" (that
	              gender only) or "Combined" (both in one column).
	standards:    a list, or a JSON list, that narrows the enquiries counted.
	"""
	_guard()

	if std_split not in STD_SPLITS:
		std_split = "Band"
	if gender_split not in GENDER_SPLITS:
		gender_split = "Split"
	if from_date and to_date and getdate(from_date) > getdate(to_date):
		frappe.throw(_("From Date cannot be after To Date."))

	standards = tuple(_parse_standards(standards))
	gender = gender_split if gender_split in GENDERS else None

	not_joined_rows = _counts(
		"Student Enquiry Form", "enquiry_date", from_date, to_date, standards, gender,
		extra="e.status != 'Converted'",
	)
	joined_rows = _counts("Student", "admission_date", from_date, to_date, standards, gender)

	genders = _gender_slots(gender_split)
	segments = {}
	unassigned = 0

	def slot(std_key, std_label, std_order, gender):
		key = f"{std_key}|{gender or 'All'}"
		if key not in segments:
			segments[key] = {
				"key": key,
				"label": std_label,
				"gender": gender,  # None when Girls and Boys are combined
				"standards": [],
				"enquired": 0,
				"joined": 0,
				"not_joined": 0,
				"_order": (std_order, genders.index(gender)),
			}
		return segments[key]

	# The default view (bands, no standard filter) always shows its full grid
	# so the layout stays put; the other views only show columns with data.
	if std_split == "Band" and not standards:
		for i, (band_key, band_label, _low, _high) in enumerate(BANDS):
			for gender in genders:
				slot(band_key, band_label, (i, ""), gender)

	for field, rows in (("not_joined", not_joined_rows), ("joined", joined_rows)):
		for r in rows:
			std = _std_slot(r, std_split, bool(standards))
			gender = r.gender if gender_split != "Combined" else None
			if not std or (gender_split != "Combined" and gender not in GENDERS):
				unassigned += r.count
				continue
			seg = slot(*std, gender)
			seg[field] += r.count
			if r.standard and r.standard not in seg["standards"]:
				seg["standards"].append(r.standard)

	ordered = sorted(segments.values(), key=lambda s: s["_order"])
	for seg in ordered:
		del seg["_order"]
		seg["enquired"] = seg["joined"] + seg["not_joined"]
		seg["conversion"] = _rate(seg["joined"], seg["enquired"])

	joined = sum(s["joined"] for s in ordered)
	not_joined = sum(s["not_joined"] for s in ordered)
	enquired = joined + not_joined

	return {
		"segments": ordered,
		"total": {
			"enquired": enquired,
			"joined": joined,
			"not_joined": not_joined,
			"conversion": _rate(joined, enquired),
		},
		# Enquiries / students in range that fit no column: no gender while genders are
		# split, or a standard that is blank or outside 6th to 12th while
		# grouping by band. They are left out of every figure; the page says so.
		"unassigned": unassigned,
	}
