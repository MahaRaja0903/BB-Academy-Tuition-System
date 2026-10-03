// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Holiday", {
	from_date(frm) {
		if (frm.doc.from_date && !frm.doc.to_date) {
			frm.set_value("to_date", frm.doc.from_date);
		}
	},
});
