"""Seed what the Performance Manager needs before a teacher can use it.

The screen is unusable out of the box without these: marking a student Bad or
Worst requires at least one Behaviour Reason, and the new doctypes are only
readable by the Performance Manager role.

Idempotent — safe to leave in patches.txt across migrates.
"""

import frappe

# Starter master list. Deliberately generic; schools rename and extend these
# from the Behaviour Reason list (or straight from the PWA's reason modal).
DEFAULT_BEHAVIOUR_REASONS = [
	("Talking in Class", "Bad"),
	("Not Doing Homework", "Bad"),
	("Disturbing Others", "Bad"),
	("Using Mobile Phone", "Bad"),
	("Disrespectful to Staff", "Both"),
	("Damaging Property", "Worst"),
	("Fighting", "Worst"),
	("Bullying", "Worst"),
	("Cheating in Test", "Worst"),
	("Leaving Without Permission", "Worst"),
]


def execute():
	_ensure_role()
	_ensure_behaviour_reasons()


def _ensure_role():
	if not frappe.db.exists("Role", "Performance Manager"):
		frappe.get_doc({"doctype": "Role", "role_name": "Performance Manager"}).insert(
			ignore_permissions=True
		)


def _ensure_behaviour_reasons():
	if not frappe.db.table_exists("Behaviour Reason"):
		return

	for reason_name, severity in DEFAULT_BEHAVIOUR_REASONS:
		if frappe.db.exists("Behaviour Reason", reason_name):
			continue
		frappe.get_doc(
			{
				"doctype": "Behaviour Reason",
				"reason_name": reason_name,
				"severity": severity,
			}
		).insert(ignore_permissions=True)
