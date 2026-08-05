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
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.trigger("status");
		}
	},
	status(frm) {
		if (frm.doc.docstatus === 0) {
			if (frm.doc.status === "Partially Paid") {
				frm.set_df_property("paid_amount", "read_only", 0);
				frm.set_df_property("paid_amount", "reqd", 1);
			} else {
				frm.set_df_property("paid_amount", "read_only", 1);
				frm.set_df_property("paid_amount", "reqd", 0);
				if (frm.doc.status === "Paid") {
					let grand_total = (frm.doc.monthly_fee || 0) + (frm.doc.arrears_amount || 0);
					frm.set_value("paid_amount", grand_total);
				} else if (frm.doc.status === "Unpaid" || frm.doc.status === "Draft") {
					frm.set_value("paid_amount", 0);
				}
			}
		}
	},
	student(frm) {
		if (frm.doc.student) {
			frappe.db.get_value(
				"Student",
				frm.doc.student,
				["standard", "current_batch", "monthly_fee", "starting_payment", "fees_due_date"],
				(r) => {
					if (r) {
						frm.set_value("standard", r.standard);
						frm.set_value("batch", r.current_batch);
						
						let currentDate = new Date();
						let monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
						let currentMonth = monthNames[currentDate.getMonth()];
						frm.set_value("fee_month", currentMonth);

						if (r.fees_due_date) {
							let year = currentDate.getFullYear();
							let month = ("0" + (currentDate.getMonth() + 1)).slice(-2);
							let day = ("0" + r.fees_due_date).slice(-2);
							frm.set_value("due_date", `${year}-${month}-${day}`);
						}

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
