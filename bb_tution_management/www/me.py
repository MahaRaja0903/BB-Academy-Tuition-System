import frappe
from frappe import _

no_cache = 1

# Modules offered on the post-login landing page.
#
# This file shadows frappe/www/me.py — Frappe's TemplatePage walks the installed
# apps in reverse order, so bb_tution_management/www/me.* wins over frappe's
# stock "My Account" page. Edit `route` here to point a tile somewhere else.
#
#   roles          — show the tile only to users holding one of these roles.
#                    An empty tuple means "everyone".
#   requires_desk  — hide the tile from Website Users (they cannot open /app/*).
MODULES = (
	{
		"key": "attendance",
		"title": "Attendance Management",
		"description": "Mark daily attendance, handle late entries and review registers.",
		"icon": "check",
		"route": "/attendance_manager",
		"roles": ("Attendance Manager", "Teacher", "Receptionist", "System Manager"),
		"requires_desk": False,
	},
	{
		"key": "student",
		"title": "Student Management",
		"description": "Admissions, batches, fee invoices and the academy dashboard.",
		"icon": "users",
		"route": "/app/bb-dashboard",
		"roles": ("System Manager", "Receptionist", "Accountant", "Owners", "Teacher"),
		"requires_desk": True,
	},
)


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/me"
		raise frappe.Redirect

	user = frappe.get_cached_doc("User", frappe.session.user)
	roles = set(frappe.get_roles())
	has_desk = user.user_type == "System User"

	context.current_user = user
	context.user_full_name = user.full_name or user.name
	context.user_abbr = "".join(p[0] for p in (user.full_name or user.name).split()[:2]).upper()
	context.modules = [
		m
		for m in MODULES
		if (not m["roles"] or roles & set(m["roles"])) and (has_desk or not m["requires_desk"])
	]

	context.no_cache = 1
	context.show_sidebar = False
	context.no_breadcrumbs = True
	context.title = _("Choose a Module")
