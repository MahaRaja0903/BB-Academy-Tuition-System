// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fees Payment Entry", {
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
	},

	calculate_totals(frm) {
		let amount = flt(frm.doc.amount);
		let discount = flt(frm.doc.discount_amount);
		let net_amount = amount - discount;
		
		let tax = 0;
		if (frm.doc.include_gst) {
			tax = net_amount * 0.18;
		}
		
		frm.set_value("tax_amount", tax);
		frm.set_value("grand_total", net_amount + tax);
	},

	amount(frm) {
		frm.trigger("calculate_totals");
	},

	discount_amount(frm) {
		frm.trigger("calculate_totals");
	},

	include_gst(frm) {
		frm.trigger("calculate_totals");
	}
});
