# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""One follow-up record per student per month.

The mistake count is never typed in: `bb_academy.mistakes` recomputes it from
the Student Performance Tracker every time a grade is saved, and the three
action levels fall out of that count. What staff fill in is what they *did*
about it -- the call, the parent meeting, the category review -- and the record
only closes once the actions its level demands are actually on file.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import cint, now_datetime


class StudentMistakeRecord(Document):
	def autoname(self):
		# Deterministic, so a second writer for the same student-month collides
		# on the primary key instead of opening a duplicate follow-up.
		from bb_tution_management.bb_academy.mistakes import record_name

		self.name = record_name(self.student, self.month_start)

	def validate(self):
		self.set_action_level()
		self.stamp_action_times()
		self.handle_status_change()

	def set_action_level(self):
		"""Levels are cumulative: a student on 6 mistakes still owes the call
		that became due at 3, on top of the parent meeting."""
		from bb_tution_management.bb_academy.mistakes import (
			LEVEL_CALL,
			LEVEL_CATEGORY,
			LEVEL_MEETING,
			THRESHOLD_CALL,
			THRESHOLD_CATEGORY,
			THRESHOLD_MEETING,
		)

		count = cint(self.mistake_count)

		self.call_required = 1 if count >= THRESHOLD_CALL else 0
		self.meeting_required = 1 if count >= THRESHOLD_MEETING else 0
		self.category_review_required = 1 if count >= THRESHOLD_CATEGORY else 0

		if count >= THRESHOLD_CATEGORY:
			self.action_level = LEVEL_CATEGORY
		elif count >= THRESHOLD_MEETING:
			self.action_level = LEVEL_MEETING
		else:
			self.action_level = LEVEL_CALL

	def stamp_action_times(self):
		"""Ticking the box is the moment it happened, unless staff say otherwise."""
		if self.call_done and not self.called_on:
			self.called_on = now_datetime()
		if self.parents_informed and not self.parents_informed_on:
			self.parents_informed_on = now_datetime()
		if self.meeting_done and not self.meeting_on:
			self.meeting_on = now_datetime()

	def handle_status_change(self):
		before = self.get_doc_before_save()
		was_closed = bool(before and before.status == "Closed")

		if self.status == "Closed":
			self.guard_closure()
			if not was_closed:
				self.closed_on = now_datetime()
				self.closed_by = frappe.session.user
				self.closed_at_count = cint(self.mistake_count)
			return

		# Open: either it never closed, or a fresh mistake reopened it.
		if was_closed:
			self.reopened_on = now_datetime()
		self.closed_on = None
		self.closed_by = None

	def guard_closure(self):
		"""Closing takes the record off the staff's list, so it may only happen
		once every action this level demands has actually been recorded."""
		# A batch move closes the record from `bb_academy.mistakes` with the
		# count already back at zero: there is no outstanding action to demand,
		# and the level the guard would check against no longer applies.
		if getattr(self.flags, "ignore_closure_guard", False):
			return

		missing = []

		if self.call_required and not self.call_done:
			missing.append("the call home has not been made")
		elif self.call_required:
			if not self.spoken_to:
				missing.append("whom the call was made to is not filled in")
			if not self.called_by:
				missing.append("who spoke from the tuition is not filled in")
			if not (self.call_notes or "").strip():
				missing.append("what was spoken is not filled in")

		if self.meeting_required:
			if not self.parents_informed:
				missing.append("the parents have not been informed")
			if not self.meeting_done:
				missing.append("the parents have not met the staff")
			else:
				if not self.met_staff:
					missing.append("the staff the parents met is not filled in")
				if not self.meeting_photo:
					missing.append("the meeting photo has not been uploaded")

		if self.category_review_required:
			unreviewed = [
				row.category for row in (self.category_breakdown or []) if not row.reviewed
			]
			if not self.category_breakdown:
				missing.append("the Test / Study / Behaviour review has not been recorded")
			elif unreviewed:
				missing.append(f"these categories are not reviewed yet: {', '.join(unreviewed)}")

		if missing:
			frappe.throw(
				frappe._("This record cannot be closed yet — {0}.").format("; ".join(missing)),
				title=frappe._("Follow-up Incomplete"),
			)
