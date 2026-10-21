# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""Start Pending Call Works counting from the month it went live.

Left blank the floor slides to the first of every month, and a family still
owed a call on the 31st would drop off the list on the 1st without anyone
having rung them. Pinning it once keeps every owed call on the list.
"""

import frappe
from frappe.utils import get_first_day, today

from bb_tution_management.bb_academy.pending_calls import DEFAULT_THRESHOLD, _setting


def execute():
	if not _setting("pending_calls_from"):
		frappe.db.set_single_value("BB Academy Settings", "pending_calls_from", get_first_day(today()))
	if not _setting("pending_call_threshold"):
		frappe.db.set_single_value("BB Academy Settings", "pending_call_threshold", DEFAULT_THRESHOLD)
