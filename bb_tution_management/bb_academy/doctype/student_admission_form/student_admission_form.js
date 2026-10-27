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

		frm.set_query("street_name", function() {
			if (frm.doc.area) {
				return {
					filters: {
						area: frm.doc.area
					}
				};
			}
		});
	},
	area(frm) {
		frm.set_value("street_name", "");
	},
	standard(frm) {
		frm.set_value('assigned_batch', '');
		frm.set_value('group', '');
		// Both fees are re-derived below, so a discount agreed for the previous
		// standard no longer applies -- and neither does the reason given for it.
		frm.set_value('reason_for_discounting_starting_amount', '');
		frm.set_value('reason_for_discounting_monthly_fees', '');
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
		// The monthly fee comes off the standard/batch pair, so a discount agreed
		// against the old batch is dropped along with it.
		frm.set_value('reason_for_discounting_monthly_fees', '');
		frm.trigger("fetch_monthly_fee");
	},

	// The checkbox is a button in disguise: it opens the same "Edit Fees Amount"
	// dialog the Student carries, and clears itself again on close so it can be
	// used more than once. Nothing is written to the database here -- the
	// admission is still being filled in, so the amount and the reason ride on
	// the form and are saved, submitted and carried to the Student with it.
	edit_fee_amount(frm) {
		if (!frm.doc.edit_fee_amount) return;

		bb_academy.show_edit_fees_dialog(
			frm,
			({ dialog, fee_type, config, new_amount, reason }) => {
				const old_amount = flt(frm.doc[fee_type]);

				frm.set_value(fee_type, new_amount);
				frm.set_value(config.reason_field, reason);

				dialog.hide();
				bb_academy.show_fee_change_alert(config, old_amount, new_amount);
			},
			() => frm.set_value("edit_fee_amount", 0)
		);
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
					}
				}
			});
		}
	},

	// Everything the quote is worked out from -- either fee, the year it falls
	// in, or the date the student joins -- re-raises the rows when it changes.
	starting_payment(frm) {
		refresh_fee_rows(frm);
	},
	monthly_fee(frm) {
		refresh_fee_rows(frm);
	},
	academic_year(frm) {
		refresh_fee_rows(frm);
	},
	application_date(frm) {
		refresh_fee_rows(frm);
	},
	date_of_joining(frm) {
		refresh_fee_rows(frm);
	},

	// A yearly student is billed one figure for the whole year. Typed in by hand
	// the month by month grid has nothing to say -- same as on the Fee Invoice;
	// auto calculated, the grid shows the months the figure is made up of.
	is_yearly_payment(frm) {
		if (frm.doc.is_yearly_payment) {
			if (frm.doc.auto_calculate_yearly_payment) {
				refresh_fee_rows(frm);
				return;
			}
			frm.clear_table("fees__invoice_details");
			frm.refresh_field("fees__invoice_details");
			calculate_total_paid(frm);
			return;
		}
		frm.set_value("auto_calculate_yearly_payment", 0);
		refresh_fee_rows(frm);
	},

	auto_calculate_yearly_payment(frm) {
		if (!frm.doc.is_yearly_payment) return;

		if (frm.doc.auto_calculate_yearly_payment) {
			if (!flt(frm.doc.monthly_fee)) {
				frappe.msgprint(__("Monthly Fee is needed to work out the yearly payment. Assign a batch first."));
			}
			refresh_fee_rows(frm);
			return;
		}

		// Back to a figure typed in by hand.
		frm.clear_table("fees__invoice_details");
		frm.refresh_field("fees__invoice_details");
		frm.set_value("total_year_payment_amount", 0);
		calculate_total_paid(frm);
	},

	yearly_fees_paid_amount(frm) {
		if (frm.doc.auto_calculate_yearly_payment) spread_yearly_paid(frm);
	}
});

// The yearly payment comes in as one amount; the grid shows it settling the
// months in order, as the Student's ledger will once the admission is submitted.
function spread_yearly_paid(frm) {
	let remaining = flt(frm.doc.yearly_fees_paid_amount);
	(frm.doc.fees__invoice_details || []).forEach(row => {
		row.paid_amount = Math.min(flt(row.amount_need_to_pay), remaining);
		remaining -= row.paid_amount;
	});
	frm.refresh_field("fees__invoice_details");
	frm.set_value("fees_paid_amount", flt(frm.doc.yearly_fees_paid_amount));
}

function refresh_yearly_rows(frm) {
	if (!flt(frm.doc.monthly_fee) || !frm.doc.academic_year) return;

	frappe.call({
		method: "bb_tution_management.bb_academy.doctype.student_admission_form.student_admission_form.get_admission_yearly_fee_rows",
		args: {
			academic_year: frm.doc.academic_year,
			application_date: frm.doc.date_of_joining || frm.doc.application_date,
			starting_payment: frm.doc.starting_payment,
			monthly_fee: frm.doc.monthly_fee
		},
		callback: function(r) {
			if (!r.message) return;

			frm.clear_table("fees__invoice_details");
			(r.message.rows || []).forEach(row => {
				frm.add_child("fees__invoice_details", {
					month: row.month,
					amount_need_to_pay: row.amount_need_to_pay,
					remarks: row.remarks
				});
			});
			frm.set_value("total_year_payment_amount", r.message.total);
			spread_yearly_paid(frm);
		}
	});
}

// The admission quotes exactly the months a Fee Invoice would raise for this
// student: the starting payment, plus the month they join -- billed by the day
// when they join after the cutoff, and left off when the starting payment
// already covers it in advance. The rules themselves stay on the server next to
// the Fee Invoice's, so the two cannot drift apart.
let fee_rows_timer = null;

function refresh_fee_rows(frm) {
	if (frm.doc.docstatus !== 0) return;
	if (frm.doc.is_yearly_payment && !frm.doc.auto_calculate_yearly_payment) return;

	// Picking a standard or a batch sets several of these fields one after the
	// other; let them settle so the server is asked once, for the finished quote.
	clearTimeout(fee_rows_timer);
	fee_rows_timer = setTimeout(() => {
		if (frm.doc.is_yearly_payment) {
			refresh_yearly_rows(frm);
			return;
		}

		if (!frm.doc.starting_payment && !frm.doc.monthly_fee) return;

		frappe.call({
			method: "bb_tution_management.bb_academy.doctype.student_admission_form.student_admission_form.get_admission_fee_rows",
			args: {
				academic_year: frm.doc.academic_year,
				application_date: frm.doc.date_of_joining || frm.doc.application_date,
				starting_payment: frm.doc.starting_payment,
				monthly_fee: frm.doc.monthly_fee
			},
			callback: function(r) {
				if (!r.message) return;

				// What the counter has already taken stays with its month; a paid
				// amount still sitting at the old full quote follows the new one.
				let previous = {};
				(frm.doc.fees__invoice_details || []).forEach(row => {
					if (row.month) previous[row.month] = row;
				});

				frm.clear_table("fees__invoice_details");
				(r.message.rows || []).forEach(row => {
					let old = previous[row.month];
					let kept_paid = old && flt(old.paid_amount) !== flt(old.amount_need_to_pay)
						? Math.min(flt(old.paid_amount), row.amount_need_to_pay)
						: row.paid_amount;

					frm.add_child("fees__invoice_details", {
						month: row.month,
						amount_need_to_pay: row.amount_need_to_pay,
						paid_amount: kept_paid,
						discount_amount: old ? old.discount_amount : 0
					});
				});
				frm.refresh_field("fees__invoice_details");
				calculate_total_paid(frm);

				(r.message.notes || []).forEach(note => {
					frappe.show_alert({ message: note, indicator: "blue" }, 10);
				});
			}
		});
	}, 300);
}

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
