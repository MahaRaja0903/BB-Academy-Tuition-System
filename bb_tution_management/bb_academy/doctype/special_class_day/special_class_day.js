// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.ui.form.on("Special Class Day", {
	scope(frm) {
		// The narrower fields are meaningless once the scope widens.
		if (frm.doc.scope === "Entire School") {
			frm.set_value("standard", null);
			frm.set_value("batch", null);
		} else if (frm.doc.scope === "Standard") {
			frm.set_value("batch", null);
		}
	},
});
