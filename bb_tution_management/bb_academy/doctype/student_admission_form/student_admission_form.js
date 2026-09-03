// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Admission Form", {
	setup(frm) {
		frm.set_query("standard", function() {
			return {
				query: "bb_tution_management.bb_academy.doctype.student_admission_form.student_admission_form.get_standard_ordered"
			};
		});
		frm.set_query("group", function() {
			if (frm.doc.standard) {
				return {
					query: "bb_tution_management.bb_tution_management.doctype.group.group.get_groups_by_standard",
					filters: {
						standard: frm.doc.standard
					}
				};
			}
		});
	},
	standard(frm) {
		frm.set_value('assigned_batch', '');
		frm.set_value('group', '');
		if (frm.doc.standard) {
			frappe.db.get_value("Standard", frm.doc.standard, "starting_payment", (r) => {
				if (r && r.starting_payment !== undefined) {
					frm.set_value("starting_payment", r.starting_payment);
				}
			});
			frm.trigger("fetch_monthly_fee");
			
			// Auto-set academic_year based on standard
			frappe.call({
				method: "bb_tution_management.bb_academy.doctype.student.student.get_academic_year_for_standard",
				args: { standard: frm.doc.standard },
				callback: function(r) {
					if (r.message) {
						frm.set_value("academic_year", r.message);
					} else {
						frm.set_value("academic_year", "");
					}
				}
			});
		} else {
			frm.set_value("academic_year", "");
		}
	},

	assigned_batch(frm) {
		frm.trigger("fetch_monthly_fee");
	},

	fetch_monthly_fee(frm) {
		if (frm.doc.standard && frm.doc.assigned_batch) {
			frappe.call({
				method: "bb_tution_management.bb_academy.doctype.student_admission_form.student_admission_form.get_monthly_fee",
				args: {
					standard: frm.doc.standard,
					batch: frm.doc.assigned_batch
				},
				callback: function(r) {
					if (r.message !== undefined) {
						frm.set_value("monthly_fee", r.message);
						
						if (frm.doc.starting_payment && (!frm.doc.fees__invoice_details || frm.doc.fees__invoice_details.length === 0)) {
							let row = frm.add_child("fees__invoice_details");
							row.month = "Starting Payment";
							row.amount_need_to_pay = frm.doc.starting_payment;
							frm.refresh_field("fees__invoice_details");
						}
					}
				}
			});
		}
	},
	starting_payment(frm) {
		if (frm.doc.fees__invoice_details && frm.doc.fees__invoice_details.length > 0) {
			let starting_row = frm.doc.fees__invoice_details.find(row => row.month === "Starting Payment");
			if (starting_row) {
				frappe.model.set_value(starting_row.doctype, starting_row.name, 'amount_need_to_pay', frm.doc.starting_payment);
			}
		}
	}
});

frappe.ui.form.on("Fees Invoice Details", {
	paid_amount: function(frm, cdt, cdn) {
		calculate_total_paid(frm);
	},
	fees__invoice_details_remove: function(frm) {
		calculate_total_paid(frm);
	}
});

function calculate_total_paid(frm) {
	let total = 0;
	if (frm.doc.fees__invoice_details) {
		frm.doc.fees__invoice_details.forEach(row => {
			total += flt(row.paid_amount);
		});
	}
	frm.set_value('fees_paid_amount', total);
}
