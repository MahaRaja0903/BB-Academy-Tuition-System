// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Admission Form", {
	setup(frm) {
		frm.set_query("standard", function() {
			return {
				order_by: "academic_order asc"
			};
		});
	},
	standard(frm) {
		if (frm.doc.standard) {
			frappe.db.get_value("Standard", frm.doc.standard, "starting_payment", (r) => {
				if (r && r.starting_payment !== undefined) {
					frm.set_value("starting_payment", r.starting_payment);
				}
			});
			frm.trigger("fetch_monthly_fee");
		}
	},

	assigned_batch(frm) {
		frm.trigger("fetch_monthly_fee");
	},

	fetch_monthly_fee(frm) {
		if (frm.doc.standard && frm.doc.assigned_batch) {
			frappe.db.get_value(
				"Fee Structure",
				{ standard: frm.doc.standard, batch: frm.doc.assigned_batch, is_active: 1 },
				"monthly_fee",
				(r) => {
					if (r && r.monthly_fee !== undefined) {
						frm.set_value("monthly_fee", r.monthly_fee);
					}
				}
			);
		}
	}
});
