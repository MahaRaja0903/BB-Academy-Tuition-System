// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

const MONTH_NAMES = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December"
];

// Fees that can be changed by hand from the "Edit Fees Amount" button.
// Labels are translated where they are used, not here -- this runs at load time.
const EDITABLE_FEES = {
	starting_payment: {
		label: "Starting Amount",
		reason_field: "reason_for_discounting_starting_amount",
	},
	monthly_fee: {
		label: "Monthly Fees",
		reason_field: "reason_for_discounting_monthly_fees",
	},
};

frappe.ui.form.on("Student", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Edit Fees Amount"), () => show_edit_fees_dialog(frm));
	},

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
		if (frm.doc.standard) {
			frm.set_value("group", "");
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

function show_edit_fees_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Edit Fees Amount"),
		fields: [
			{
				fieldname: "fee_type",
				fieldtype: "Select",
				label: __("Which fee do you want to edit?"),
				reqd: 1,
				options: [
					{ value: "", label: "" },
					...Object.keys(EDITABLE_FEES).map((fee_type) => ({
						value: fee_type,
						label: __(EDITABLE_FEES[fee_type].label),
					})),
				],
				onchange: () => on_fee_type_selected(frm, dialog),
			},
			{
				fieldname: "current_amount",
				fieldtype: "Currency",
				label: __("Current Amount"),
				read_only: 1,
				depends_on: "fee_type",
			},
			{
				fieldname: "new_amount",
				fieldtype: "Currency",
				label: __("New Amount"),
				depends_on: "fee_type",
			},
			{ fieldtype: "Section Break", depends_on: "fee_type" },
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Reason"),
				depends_on: "fee_type",
				description: __("Recorded against the student along with the new amount."),
			},
		],
		primary_action_label: __("Update"),
		primary_action: (values) => submit_fee_change(frm, dialog, values),
	});

	dialog.show();
}

// Show what the selected fee is currently set to, and pre-fill the reason
// already recorded against it (if any) so it can be reviewed or reworded.
function on_fee_type_selected(frm, dialog) {
	const fee_type = dialog.get_value("fee_type");
	if (!fee_type) {
		dialog.set_value("current_amount", 0);
		dialog.set_value("new_amount", 0);
		dialog.set_value("reason", "");
		return;
	}

	const config = EDITABLE_FEES[fee_type];
	const current_amount = frm.doc[fee_type] || 0;

	dialog.set_value("current_amount", current_amount);
	dialog.set_value("new_amount", current_amount);
	dialog.set_value("reason", frm.doc[config.reason_field] || "");
	dialog.set_df_property("new_amount", "label", __("New {0}", [__(config.label)]));
}

function submit_fee_change(frm, dialog, values) {
	const config = EDITABLE_FEES[values.fee_type];

	const new_amount = flt(values.new_amount);
	if (new_amount < 0) {
		frappe.msgprint(__("Fees amount cannot be negative."));
		return;
	}

	const reason = (values.reason || "").trim();
	if (!reason) {
		frappe.msgprint(__("Please enter a reason for changing the {0}.", [__(config.label)]));
		return;
	}

	frappe.call({
		method: "bb_tution_management.bb_academy.doctype.student.student.update_fee_amount",
		args: {
			student: frm.doc.name,
			fee_type: values.fee_type,
			new_amount: new_amount,
			reason: reason,
		},
		freeze: true,
		freeze_message: __("Updating fees..."),
		callback: (r) => {
			if (!r.message) return;

			dialog.hide();
			frm.reload_doc();
			frappe.show_alert({
				message: __("{0} updated from {1} to {2}", [
					__(config.label),
					format_currency(r.message.old_amount, frappe.defaults.get_default("currency")),
					format_currency(r.message.new_amount, frappe.defaults.get_default("currency")),
				]),
				indicator: "green",
			});
		},
	});
}
