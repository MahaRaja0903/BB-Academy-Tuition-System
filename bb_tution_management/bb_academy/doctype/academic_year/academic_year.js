// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

const monthNames = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December"
];

frappe.ui.form.on("Academic Year", {
	start_date(frm) {
		if (frm.doc.start_date) {
			const d = new Date(frm.doc.start_date);
			if (!isNaN(d.getTime())) {
				frm.set_value("start_month", monthNames[d.getMonth()]);
			}
		}
	},
	end_date(frm) {
		if (frm.doc.end_date) {
			const d = new Date(frm.doc.end_date);
			if (!isNaN(d.getTime())) {
				frm.set_value("end_month", monthNames[d.getMonth()]);
			}
		}
	}
});
