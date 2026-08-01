// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student", {
	onload(frm) {
		if (!frm.doc.academic_year) {
			let today = frappe.datetime.get_today();
			if (today) {
				let year = parseInt(today.split('-')[0]);
				let month = parseInt(today.split('-')[1]);
				
				let start_year = month >= 6 ? year : year - 1;
				let end_year = start_year + 1;
				
				frm.set_value("academic_year", `${start_year}-${end_year}`);
			}
		}
	},
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

	current_batch(frm) {
		frm.trigger("fetch_monthly_fee");
	},

	fetch_monthly_fee(frm) {
		if (frm.doc.standard && frm.doc.current_batch) {
			frappe.db.get_value(
				"Fee Structure",
				{ standard: frm.doc.standard, batch: frm.doc.current_batch },
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
