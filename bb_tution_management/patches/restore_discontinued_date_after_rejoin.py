"""Rejoining used to clear the Discontinued Date on the Student. Put the date
back from each student's latest Student Rejoin Log, so it shows after rejoin."""

import frappe


def execute():
	logs = frappe.db.sql(
		"""
		SELECT l.student, l.discontinued_date
		FROM `tabStudent Rejoin Log` l
		JOIN `tabStudent` s ON s.name = l.student
		WHERE l.discontinued_date IS NOT NULL
			AND s.discontinued__date IS NULL
			AND s.status != 'Discontinued'
		ORDER BY l.student, l.rejoined_date, l.creation
		""",
		as_dict=True,
	)
	latest = {}
	for log in logs:
		latest[log.student] = log.discontinued_date  # last one wins

	for student, date in latest.items():
		frappe.db.set_value("Student", student, "discontinued__date", date, update_modified=False)
