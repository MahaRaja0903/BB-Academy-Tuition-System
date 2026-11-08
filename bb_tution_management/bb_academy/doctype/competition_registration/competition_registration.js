// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.ui.form.on("Competition Registration", {
	setup(frm) {
		frm.set_query("competition", () => ({ filters: { is_active: 1 } }));
	},
});
