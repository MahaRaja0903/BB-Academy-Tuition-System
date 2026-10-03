// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

const MONTH_NAMES = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December"
];

frappe.ui.form.on("Student", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Edit Fees Amount"), () => show_edit_fees_dialog(frm));

		frm.add_custom_button(__("Add to WhatsApp Group"), () => {
			if (!frm.doc.standard) {
				frappe.msgprint(__("Please select a Standard first."));
				return;
			}
			frappe.db.get_value("Standard", frm.doc.standard, "whatsapp_group_link", (r) => {
				if (r && r.whatsapp_group_link) {
					window.open(r.whatsapp_group_link, '_blank');
				} else {
					frappe.msgprint(__("WhatsApp Group Link is not configured for this Standard."));
				}
			});
		});
	},

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
	standard(frm) {
		if (frm.doc.standard) {
			frm.set_value("group", "");
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

	area(frm) {
		frm.set_value("street_name", "");
	},

	current_batch(frm) {
		frm.trigger("fetch_monthly_fee");
	},

	fetch_monthly_fee(frm) {
		if (frm.doc.standard && frm.doc.current_batch) {
			// "standard" on Fee Structure is a Table MultiSelect, so it cannot be
			// used as a filter column -- go through the server-side helper instead.
			frappe.call({
				method: "bb_tution_management.bb_academy.doctype.student_admission_form.student_admission_form.get_monthly_fee",
				args: {
					standard: frm.doc.standard,
					batch: frm.doc.current_batch,
				},
				callback: (r) => {
					if (r.message !== undefined) {
						frm.set_value("monthly_fee", r.message);
					}
				},
			});
		}
	},

	scholarship_student(frm) {
		if (frm.doc.scholarship_student) {
			(frm.doc.payment_details || []).forEach((row) => {
				if (row.status === "Not Paid") {
					row.status = "Paid";
				}
			});
			frm.refresh_field("payment_details");
		}
	},

	academic_year(frm) {
		frm.trigger("populate_payment_details");
	},

	admission_date(frm) {
		frm.trigger("populate_payment_details");
	},

	populate_payment_details(frm) {
		if (!frm.doc.academic_year || !frm.doc.admission_date) {
			return;
		}

		frappe.db.get_value(
			"Academic Year",
			frm.doc.academic_year,
			["start_date", "end_date"],
			(ay) => {
				if (!ay || !ay.start_date || !ay.end_date) return;

				let start_parts = ay.start_date.split('-');
				let end_parts = ay.end_date.split('-');
				let start_y = parseInt(start_parts[0], 10);
				let start_m = parseInt(start_parts[1], 10) - 1; // 0-based
				let end_y = parseInt(end_parts[0], 10);
				let end_m = parseInt(end_parts[1], 10) - 1; // 0-based

				let total_months = (end_y - start_y) * 12 + (end_m - start_m) + 1;
				if (total_months <= 0) return;

				// Build ordered list of month indices (0-based) from start to end
				let academic_months = [];
				let idx = start_m;
				for (let i = 0; i < total_months; i++) {
					academic_months.push(idx % 12);
					idx++;
				}

				// Get admission month (0-based)
				let ad_parts = frm.doc.admission_date.split('-');
				let admission_month_idx = parseInt(ad_parts[1]) - 1;  // 0-based

				// Find admission position in academic calendar
				let admission_pos = academic_months.indexOf(admission_month_idx);
				if (admission_pos === -1) {
					// Admission month not in academic calendar, treat as joined from start
					admission_pos = 0;
				}

				// Build lookup of existing rows with meaningful statuses to preserve
				let existing = {};
				(frm.doc.payment_details || []).forEach((row) => {
					let mi = MONTH_NAMES.indexOf(row.month);
					if (mi !== -1 && row.status && !["Not Joined", "Not Paid"].includes(row.status)) {
						existing[mi] = row;
					}
				});

				// Clear and rebuild
				frm.doc.payment_details = [];
				frm.clear_table("payment_details");

				academic_months.forEach((month_idx, pos) => {
					let month_name = MONTH_NAMES[month_idx];

					if (existing[month_idx]) {
						let kept = existing[month_idx];
						let row = frm.add_child("payment_details");
						row.month = kept.month;
						row.date = kept.date;
						row.status = kept.status;
						row.amount_paid = kept.amount_paid;
						row.pending = kept.pending;
						row.coupon_amount = kept.coupon_amount;
					} else {
						let status = pos < admission_pos ? "Not Joined" : "Not Paid";
						if (frm.doc.scholarship_student && status === "Not Paid") {
							status = "Paid";
						}
						let row = frm.add_child("payment_details");
						row.month = month_name;
						row.status = status;
					}
				});

				frm.refresh_field("payment_details");
				frm.dirty();
			}
		);
	}
});

// The dialog itself is shared with the Student Admission Form; here it writes
// straight to the saved Student record.
function show_edit_fees_dialog(frm) {
	bb_academy.show_edit_fees_dialog(frm, ({ dialog, fee_type, config, new_amount, reason }) => {
		frappe.call({
			method: "bb_tution_management.bb_academy.doctype.student.student.update_fee_amount",
			args: {
				student: frm.doc.name,
				fee_type: fee_type,
				new_amount: new_amount,
				reason: reason,
			},
			freeze: true,
			freeze_message: __("Updating fees..."),
			callback: (r) => {
				if (!r.message) return;

				dialog.hide();
				frm.reload_doc();
				bb_academy.show_fee_change_alert(config, r.message.old_amount, r.message.new_amount);
			},
		});
	});
}
