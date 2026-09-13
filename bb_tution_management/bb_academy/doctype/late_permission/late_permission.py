# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class LatePermission(Document):
	def before_insert(self):
		"""Keep `time` blank unless a time was actually recorded.

		`Document.insert()` runs `_set_defaults()`, which stamps `nowtime()`
		onto every Time field via `frappe.model.create_new` -- unconditionally,
		with no default declared -- so a permission saved without a time landed
		with the moment it was saved instead. `time` is optional on this
		doctype, and "not recorded" has to stay distinguishable from a real
		entry time.

		`update_if_missing()` cannot tell a caller's explicit `None` from an
		omitted field, so the caller marks its intent with `flags.time_given`
		and this hook restores the blank. `before_insert` runs after
		`_set_defaults()`, so it has the last word.
		"""
		if not self.flags.time_given:
			self.time = None
