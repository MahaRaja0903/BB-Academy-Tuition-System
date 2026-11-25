"""Re-tag as "Discontinued" the Absent rows staff had to mark for students while they were
discontinued. Those days now read as "Discontinued" (derived from the Student
and the Student Rejoin Log), not as absences."""

import frappe

from bb_tution_management.bb_academy.discontinue import (
	tag_discontinued_absences,
	get_discontinued_periods,
)


def execute():
	removed = 0
	for student, spans in get_discontinued_periods().items():
		for start, end in spans:
			removed += tag_discontinued_absences(student, start, end)
	print(f"Re-tagged {removed} Absent rows marked while students were discontinued")
