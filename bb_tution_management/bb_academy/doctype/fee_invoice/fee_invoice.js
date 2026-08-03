// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fee Invoice", {
	setup(frm) {
		frm.set_query("standard", function() {
			return {
				order_by: "academic_order asc"
			};
		});
	},
	student(frm) {
		if (frm.doc.student) {
			frappe.db.get_value(
				"Student",
				frm.doc.student,
				["standard", "current_batch", "monthly_fee", "starting_payment"],
				(r) => {
					if (r) {
						frm.set_value("standard", r.standard);
						frm.set_value("batch", r.current_batch);
						
						let monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
						let currentMonth = monthNames[new Date().getMonth()];
						frm.set_value("fee_month", currentMonth);

						if (frm.doc.is_starting_fee) {
							frm.set_value("monthly_fee", r.starting_payment || 0);
						} else {
							frm.set_value("monthly_fee", r.monthly_fee || 0);
						}
					}
				}
			);
		}
	},
	is_starting_fee(frm) {
		if (frm.doc.student) {
			frm.trigger("student");
		}
	}
});
