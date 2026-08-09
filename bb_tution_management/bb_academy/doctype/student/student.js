// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

const MONTH_NAMES = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December"
];

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
			["start_month", "end_month"],
			(ay) => {
				if (!ay || !ay.start_month || !ay.end_month) return;

				let start_idx = MONTH_NAMES.indexOf(ay.start_month);
				let end_idx = MONTH_NAMES.indexOf(ay.end_month);

				if (start_idx === -1 || end_idx === -1) return;

				// Build ordered list of month indices (0-based) from start to end
				let academic_months = [];
				let idx = start_idx;
				while (true) {
					academic_months.push(idx);
					if (idx === end_idx) break;
					idx = (idx + 1) % 12;
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
