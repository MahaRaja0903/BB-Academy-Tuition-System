// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payment Entry", {
	setup(frm) {
		frm.set_query("fee_invoice", () => {
			return {
				filters: {
					student: frm.doc.student || "",
					docstatus: 1,
					status: ["in", ["Unpaid", "Partially Paid"]]
				}
			};
		});
	},

	fee_invoice(frm) {
		if (frm.doc.fee_invoice) {
			frappe.db.get_value(
				"Fee Invoice",
				frm.doc.fee_invoice,
				["student", "outstanding_amount"],
				(r) => {
					if (r) {
						if (r.student && !frm.doc.student) {
							frm.set_value("student", r.student);
						}
						if (r.outstanding_amount !== undefined && !frm.doc.amount) {
							frm.set_value("amount", r.outstanding_amount);
						}
					}
				}
			);
		}
	}
});
