"""Read-only data feeds for external consumers (e.g. the AI / analytics side).

Call with a Frappe API key of a user that can read the doctypes:

	GET /api/method/bb_tution_management.bb_academy.data_api.get_attendance_data
	GET /api/method/bb_tution_management.bb_academy.data_api.get_performance_data
	Authorization: token <api_key>:<api_secret>

Both are paginated with `start` / `page_length` and return
`{"total": n, "start": s, "page_length": p, "data": [...]}`.
"""

import frappe
from frappe.utils import cint, getdate

MAX_PAGE_LENGTH = 5000

# Table MultiSelect fields on Student Performance Tracker -> (child doctype, link field)
PERFORMANCE_CHILD_TABLES = {
	"subjects": ("Subject Item", "subject"),
	"lessons": ("Lesson Item", "lesson"),
	"portions": ("Portion Item", "portion"),
	"behaviour_reasons": ("Student Behaviour Reason Item", "behaviour_reason"),
}


def _common_filters(date_field, from_date, to_date, student, standard, batch):
	filters = {}
	if from_date and to_date:
		filters[date_field] = ["between", [getdate(from_date), getdate(to_date)]]
	elif from_date:
		filters[date_field] = [">=", getdate(from_date)]
	elif to_date:
		filters[date_field] = ["<=", getdate(to_date)]
	if student:
		filters["student"] = student
	if standard:
		filters["standard"] = standard
	if batch:
		filters["batch"] = batch
	return filters


def _page(start, page_length):
	start = max(cint(start), 0)
	page_length = cint(page_length) or 1000
	return start, min(max(page_length, 1), MAX_PAGE_LENGTH)


@frappe.whitelist(methods=["GET", "POST"])
def get_attendance_data(
	from_date=None, to_date=None, student=None, standard=None, batch=None, status=None, start=0, page_length=1000
):
	"""All Student Attendance rows matching the filters, oldest first."""
	if not frappe.has_permission("Student Attendance", "read"):
		frappe.throw("No permission to read attendance records", frappe.PermissionError)

	filters = _common_filters("attendance_date", from_date, to_date, student, standard, batch)
	if status:
		filters["status"] = status
	start, page_length = _page(start, page_length)

	data = frappe.get_list(
		"Student Attendance",
		filters=filters,
		fields=[
			"name",
			"student",
			"student_name",
			"standard",
			"batch",
			"attendance_date",
			"status",
			"remarks",
			"early_out_time",
			"early_out_reason",
			"second_time_attendance_date",
			"second_time_attendance_status",
		],
		order_by="attendance_date asc, student asc",
		limit_start=start,
		limit_page_length=page_length,
	)
	for row in data:
		if row.early_out_time is not None:
			row.early_out_time = str(row.early_out_time)

	return {
		"total": frappe.db.count("Student Attendance", filters),
		"start": start,
		"page_length": page_length,
		"data": data,
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_performance_data(
	from_date=None,
	to_date=None,
	student=None,
	standard=None,
	batch=None,
	category=None,
	include_skipped=0,
	start=0,
	page_length=1000,
):
	"""All Student Performance Tracker rows matching the filters, oldest first,
	with subjects / lessons / portions / behaviour reasons flattened to lists."""
	if not frappe.has_permission("Student Performance Tracker", "read"):
		frappe.throw("No permission to read performance records", frappe.PermissionError)

	filters = _common_filters("date", from_date, to_date, student, standard, batch)
	if category:
		filters["category"] = category
	if not cint(include_skipped):
		filters["skipped"] = 0
	start, page_length = _page(start, page_length)

	data = frappe.get_list(
		"Student Performance Tracker",
		filters=filters,
		fields=[
			"name",
			"student",
			"student_name",
			"standard",
			"batch",
			"date",
			"category",
			"result",
			"skipped",
			"session",
			"subject",
			"total_questions",
			"total_marks",
			"pass_marks",
			"marks_obtained",
			"remarks",
		],
		order_by="date asc, student asc",
		limit_start=start,
		limit_page_length=page_length,
	)

	names = [row.name for row in data]
	children = {}
	for fieldname, (child_doctype, link_field) in PERFORMANCE_CHILD_TABLES.items():
		values = {}
		if names:
			for child in frappe.get_all(
				child_doctype,
				filters={
					"parenttype": "Student Performance Tracker",
					"parentfield": fieldname,
					"parent": ["in", names],
				},
				fields=["parent", link_field],
				order_by="idx asc",
			):
				values.setdefault(child.parent, []).append(child[link_field])
		children[fieldname] = values

	for row in data:
		for fieldname, values in children.items():
			row[fieldname] = values.get(row.name, [])

	return {
		"total": frappe.db.count("Student Performance Tracker", filters),
		"start": start,
		"page_length": page_length,
		"data": data,
	}
