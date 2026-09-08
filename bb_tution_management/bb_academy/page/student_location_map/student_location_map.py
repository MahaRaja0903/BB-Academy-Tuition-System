"""Student Location Map — data layer.

Coordinates are never derived here. `Student.latitude` / `Student.longitude`
are typed in by hand on the Student form (see `Student.validate_map_coordinates`),
and this module only reads them. There is no geocoding, no address lookup and no
external service call anywhere in this feature — the map is drawn client-side by
Leaflet over OpenStreetMap tiles.

Frappe stores an unset Float as 0.0 rather than NULL, so "has no location" means
*falsy or out of range* throughout: a 0/0 pair is the Gulf of Guinea, never a
real student address, and is treated as missing.

Student location is sensitive, so every endpoint below guards itself. Page-level
role checks in student_location_map.json only hide the UI; a whitelisted method
is callable directly, so the guard has to live at the source.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

# Roles allowed to read student locations. Administrator always passes.
# Deliberately narrow — this is the one screen that plots where children live.
# Widen it here (and in student_location_map.json) if the academy wants e.g.
# Receptionist to have it too.
ALLOWED_ROLES = {"System Manager", "Attendance Manager"}

# Fields sent to the browser. Only what the map, the popup card and the
# "students without location" table actually render — never the whole document,
# which carries fees, parent phone numbers and payment history.
MAP_FIELDS = (
	"name",
	"student_name",
	"image",
	"gender",
	"standard",
	"current_batch",
	"area",
	"street_name",
	"address",
	"latitude",
	"longitude",
)

# Rows per round-trip. The page walks the pages until the server says there are
# no more, so a 5,000-student academy costs 3 requests, not 5,000.
DEFAULT_PAGE_LENGTH = 1000
MAX_PAGE_LENGTH = 2000


def _guard():
	"""Refuse anyone who is not allowed to see where students live."""
	if frappe.session.user == "Administrator":
		return

	if not (ALLOWED_ROLES & set(frappe.get_roles())):
		frappe.throw(
			_("You are not permitted to view student locations."),
			frappe.PermissionError,
		)

	# Belt and braces: the role could be granted without Student read access.
	if not frappe.has_permission("Student", "read"):
		raise frappe.PermissionError(_("Not permitted to read Student records."))


def has_valid_coordinates(latitude, longitude) -> bool:
	"""A pair is usable only when both values are set and in range.

	0.0 is how Frappe stores an empty Float, so it reads as "not set" here —
	the same rule the Student controller applies when validating input.
	"""
	lat, lng = flt(latitude), flt(longitude)
	if not lat or not lng:
		return False
	return -90 <= lat <= 90 and -180 <= lng <= 180


def _split(rows):
	"""Partition one page of students into plottable and not-yet-plottable."""
	located, unlocated = [], []

	for row in rows:
		if has_valid_coordinates(row.get("latitude"), row.get("longitude")):
			located.append(
				{
					"name": row["name"],
					"student_name": row.get("student_name"),
					"image": row.get("image"),
					"gender": row.get("gender"),
					"standard": row.get("standard"),
					"batch": row.get("current_batch"),
					"area": row.get("area"),
					"street_name": row.get("street_name"),
					"address": row.get("address"),
					"latitude": flt(row.get("latitude")),
					"longitude": flt(row.get("longitude")),
				}
			)
		else:
			unlocated.append(
				{
					"name": row["name"],
					"student_name": row.get("student_name"),
					"gender": row.get("gender"),
					"standard": row.get("standard"),
					"batch": row.get("current_batch"),
					"area": row.get("area"),
					"street_name": row.get("street_name"),
				}
			)

	return located, unlocated


@frappe.whitelist()
def get_students(limit_start=0, page_length=DEFAULT_PAGE_LENGTH):
	"""One page of students, already split by whether they can be mapped.

	Returned in a stable `name` order so paging cannot skip or repeat a student
	while the page walks through it.
	"""
	_guard()

	limit_start = max(cint(limit_start), 0)
	page_length = min(max(cint(page_length) or DEFAULT_PAGE_LENGTH, 1), MAX_PAGE_LENGTH)

	rows = frappe.get_all(
		"Student",
		fields=list(MAP_FIELDS),
		order_by="name asc",
		limit_start=limit_start,
		limit_page_length=page_length,
		ignore_permissions=False,
	)

	located, unlocated = _split(rows)

	return {
		"located": located,
		"unlocated": unlocated,
		"limit_start": limit_start,
		"page_length": page_length,
		"returned": len(rows),
		# A short page means the table is exhausted; a full one means ask again.
		"has_more": len(rows) == page_length,
	}


@frappe.whitelist()
def get_students_without_location(limit_start=0, page_length=DEFAULT_PAGE_LENGTH):
	"""Students still missing coordinates, for the administrator's worklist.

	The map page already holds this list from `get_students`, so it never calls
	this. It exists so the worklist can be pulled on its own — from a script or
	a follow-up screen — without dragging every located student along with it.
	"""
	_guard()

	limit_start = max(cint(limit_start), 0)
	page_length = min(max(cint(page_length) or DEFAULT_PAGE_LENGTH, 1), MAX_PAGE_LENGTH)

	# The columns are decimal NOT NULL DEFAULT 0, so "never entered" is exactly
	# 0 -- there is no NULL case to catch. An out-of-range value cannot get in
	# through the form (the controller rejects it) and is rare enough to leave
	# to the Python check in `_split`.
	rows = frappe.get_all(
		"Student",
		fields=list(MAP_FIELDS),
		or_filters=[
			["latitude", "=", 0],
			["longitude", "=", 0],
		],
		order_by="name asc",
		limit_start=limit_start,
		limit_page_length=page_length,
	)

	_, unlocated = _split(rows)

	return {
		"students": unlocated,
		"limit_start": limit_start,
		"page_length": page_length,
		"returned": len(rows),
		"has_more": len(rows) == page_length,
	}
