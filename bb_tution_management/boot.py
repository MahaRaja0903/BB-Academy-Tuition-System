import frappe

def boot_session(bootinfo):
	"""Set the default home page after login, based on role.

	"bb-dashboard" does not grant access to the Attendance Manager role, so
	sending those users there unconditionally left them on a page they can't
	view. Send Attendance-Manager-only users to "attendance-dashboard" instead.
	"""
	if frappe.session.user == "Guest":
		return

	roles = frappe.get_roles()

	if "System Manager" not in roles and "Administrator" not in roles and "Attendance Manager" in roles:
		bootinfo["home_page"] = "attendance-dashboard"
	else:
		bootinfo["home_page"] = "bb-dashboard"
