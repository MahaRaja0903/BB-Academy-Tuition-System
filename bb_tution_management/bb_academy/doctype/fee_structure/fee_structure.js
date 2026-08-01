// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fee Structure", {
	setup(frm) {
		frm.set_query("standard", "standard", function() {
			return {
				order_by: "academic_order asc"
			};
		});
	},
	refresh(frm) {

	},
});
