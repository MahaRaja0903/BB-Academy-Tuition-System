import frappe

def boot_session(bootinfo):
	"""Set the custom dashboard as the default home page after login"""
	if frappe.session.user != "Guest":
		bootinfo["home_page"] = "bb-dashboard"
