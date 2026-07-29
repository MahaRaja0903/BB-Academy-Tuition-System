// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fee Invoice", {
	student(frm) {
		if (frm.doc.student) {
			frappe.db.get_value(
				"Student",
				frm.doc.student,
				["standard", "current_batch", "monthly_fee"],
				(r) => {
					if (r) {
						frm.set_value("standard", r.standard);
						frm.set_value("batch", r.current_batch);
						frm.set_value("monthly_fee", r.monthly_fee || 0);
					}
				}
			);
		}
	}
});
