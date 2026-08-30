// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

// A month settled out of the starting payment rather than paid for on its own,
// and a month the starting payment has booked but not yet paid for. Kept in step
// with the same names in fee_invoice.py.
const PAID_BY_STARTING_PAYMENT = "Paid By Starting Payment";
const RESERVED = "Reserved";

const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
	'July', 'August', 'September', 'October', 'November', 'December'];

const MONTH_SHORT = {
	January: 'Jan', February: 'Feb', March: 'Mar', April: 'Apr', May: 'May', June: 'Jun',
	July: 'Jul', August: 'Aug', September: 'Sep', October: 'Oct', November: 'Nov', December: 'Dec'
};

// The months of the student's own academic year, in the order that year runs --
// a June-to-April year starts at June, not April. get_student_fee_data works
// them out from the Academic Year; the April-to-March list is only a fallback
// for a student who has no academic year set yet.
function get_academic_month_list(data) {
	let months = (data && data.academic_months) || [];
	if (months.length) {
		return months;
	}
	return ['April', 'May', 'June', 'July', 'August', 'September',
		'October', 'November', 'December', 'January', 'February', 'March'];
}

// 'YYYY-MM-DD' through new Date() is read as UTC midnight, which slides back a
// day in any timezone behind it -- enough to make a payment look a day later
// than it was. Read the parts off the string instead.
function parse_iso_date(value) {
	let parts = String(value || '').slice(0, 10).split('-');
	if (parts.length !== 3) {
		return null;
	}
	return { year: +parts[0], month: +parts[1], day: +parts[2] };
}

// 5 -> "th", 1 -> "st" ... for spelling a due date as "5th of August".
function ordinal(day) {
	day = parseInt(day, 10);
	if (!day) return '';
	if (day === 1 || day === 21 || day === 31) return 'st';
	if (day === 2 || day === 22) return 'nd';
	if (day === 3 || day === 23) return 'rd';
	return 'th';
}

// Whether a month's fee landed after the day it was due, and by how much.
//
// Late is measured against the student's own Fees Due Date -- most run on the
// 5th, so a fixed "after the 15th" rule would call a payment on the 8th prompt
// when it was three days overdue. A payment made in a later month of the year
// is late whatever the day; one made in an earlier month was paid in advance.
function get_payment_timing(data, months, month, pd_date) {
	let due_day = parseInt(data && data.fees_due_date, 10);
	if (!pd_date || !due_day) {
		// No due date on file -- nothing to judge the payment against.
		return { late: false, days: null };
	}

	let admission = parse_iso_date(data && data.admission_date);
	if (admission
		&& MONTH_NAMES[admission.month - 1] === month
		&& admission.day > due_day) {
		// The student joined during this month, after the day its fee would
		// have fallen due. That date passed before they were enrolled, so this
		// month has no due date of its own to judge the payment against -- and
		// this is the pro-rated joining month anyway, billed from the admission
		// date rather than for the whole month.
		return { late: false, days: null };
	}

	let paid = parse_iso_date(pd_date);
	if (!paid) {
		return { late: false, days: null };
	}
	let paid_month = MONTH_NAMES[paid.month - 1];

	if (paid_month === month) {
		let days = paid.day - due_day;
		return days > 0 ? { late: true, days: days } : { late: false, days: null };
	}

	let fee_idx = months.indexOf(month);
	let paid_idx = months.indexOf(paid_month);
	if (fee_idx !== -1 && paid_idx !== -1 && paid_idx > fee_idx) {
		return { late: true, days: null };
	}

	return { late: false, days: null };
}

// How far into that year the student joined, so the months before it read as
// Not Joined. Measured by position in the year's own month list rather than by
// calendar month number.
function get_admission_index(data, months) {
	if (!data || !data.admission_date) {
		return 0;
	}
	let admission = parse_iso_date(data.admission_date);
	if (!admission) {
		return 0;
	}
	let idx = months.indexOf(MONTH_NAMES[admission.month - 1]);
	return idx === -1 ? 0 : idx;
}

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
		// Render student fee tracking on refresh if student is set
		if (frm.doc.student) {
			frm.trigger("render_fee_tracking");
		} else {
			// Clear stale HTML from a previously viewed invoice
			if (frm.fields_dict.student_html) {
				frm.fields_dict.student_html.$wrapper.html("");
			}
			if (frm.fields_dict.fees_paid_details_html) {
				frm.fields_dict.fees_paid_details_html.$wrapper.html("");
			}
		}

		// The bill only means anything once the payment is actually posted.
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Generate Bill"), () => generate_bill(frm));
		}
	},
	before_submit(frm) {
		// Submitting posts the money against the student's months and cannot be
		// undone without cancelling, so make the cashier confirm what was taken.
		frappe.validated = false;

		return new Promise((resolve) => {
			let dialog = new frappe.ui.Dialog({
				title: __("Confirm Amount Collected"),
				fields: [{
					fieldtype: "HTML",
					fieldname: "collection_summary",
					options: build_collection_summary_html(frm)
				}],
				primary_action_label: __("Amount Collected — Submit"),
				primary_action() {
					frappe.validated = true;
					resolve();
					dialog.hide();
				},
				secondary_action_label: __("Go Back")
			});

			// Dismissing the dialog leaves frappe.validated false, which stops the
			// submit -- but the promise still has to settle or the form hangs.
			dialog.$wrapper.on("hidden.bs.modal", () => resolve());
			dialog.show();
		});
	},
	student(frm) {
		// Coupons belong to the student they were issued to.
		if (frm.doc.docstatus === 0 && frm.doc.coupon__code) {
			frm.set_value("coupon__code", "");
			frm.set_value("coupon_amount", 0);
		}

		if (!frm.doc.student) {
			frm.clear_table("fees_details");
			frm.refresh_field("fees_details");
			frm.set_value("is_starting_fee", 0);
			update_monthly_fee_from_details(frm);
			frm.fields_dict.student_html.$wrapper.html("");
			return;
		}

		// Render fee tracking UI (also caches the student data in student_detail_json)
		frm.trigger("render_fee_tracking");

		if (frm.doc.docstatus !== 0) return;

		// Seed the grid with whatever the student currently owes: any pending
		// starting payment, plus the current month unless it is already paid or
		// covered by the starting payment advance.
		frappe.call({
			method: "bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice.get_invoice_prefill",
			args: { student: frm.doc.student },
			callback: function(r) {
				if (!r.message) return;
				let prefill = r.message;

				frm.clear_table("fees_details");
				(prefill.rows || []).forEach(row => {
					frm.add_child("fees_details", {
						month: row.month,
						amount_need_to_pay: row.amount_need_to_pay,
						paid_amount: row.paid_amount
					});
				});
				frm.refresh_field("fees_details");

				// After the rows exist, so the is_starting_fee handler sees the
				// Starting Payment row already there and leaves it alone.
				frm.set_value("is_starting_fee", prefill.has_starting_payment ? 1 : 0);
				update_monthly_fee_from_details(frm);

				(prefill.notes || []).forEach(note => {
					frappe.show_alert({ message: note, indicator: "blue" }, 10);
				});
			}
		});
	},
	is_starting_fee(frm) {
		let existing = frm.doc.fees_details || [];
		let has_row = existing.some(d => d.month === "Starting Payment");

		if (frm.doc.is_starting_fee && !has_row) {
			frm.add_child("fees_details", {
				month: "Starting Payment",
				amount_need_to_pay: get_row_amount(frm, "Starting Payment"),
				paid_amount: get_row_amount(frm, "Starting Payment")
			});
			frm.refresh_field("fees_details");
		} else if (!frm.doc.is_starting_fee && has_row) {
			frm.doc.fees_details = existing.filter(d => d.month !== "Starting Payment");
			frm.doc.fees_details.forEach((row, idx) => { row.idx = idx + 1; });
			frm.refresh_field("fees_details");
		} else {
			return;
		}

		update_monthly_fee_from_details(frm);
	},
	fees_details_remove(frm) {
		update_monthly_fee_from_details(frm);
	},
	add_coupon(frm) {
		if (frm.doc.docstatus !== 0) {
			frappe.msgprint(__("Coupons can only be changed while the invoice is a draft."));
			return;
		}
		if (!frm.doc.student) {
			frappe.msgprint(__("Select a Student first."));
			return;
		}

		frappe.call({
			method: "bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice.get_available_coupons",
			args: { student: frm.doc.student },
			callback: function(r) {
				let coupons = r.message || [];

				if (!coupons.length) {
					frappe.msgprint({
						title: __("No Coupons Available"),
						message: __("{0} has no unused coupon that is still valid.",
							[frm.doc.student_name || frm.doc.student]),
						indicator: "orange"
					});
					return;
				}

				show_coupon_dialog(frm, coupons);
			}
		});
	},
	render_fee_tracking(frm) {
		if (!frm.doc.student) {
			frm.fields_dict.student_html.$wrapper.html("");
			return;
		}
		frappe.call({
			method: "bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice.get_student_fee_data",
			args: { student: frm.doc.student },
			callback: function(r) {
				if (r.message) {
					let data = r.message;
					// Store as JSON
					if (frm.doc.docstatus === 0){
						frm.set_value("student_detail_json", JSON.stringify(data));
					}

					// is_starting_fee and the Fees Details rows are set by
					// get_invoice_prefill when the student is picked -- don't
					// second-guess them on every refresh.

					// Build and render HTML
					let student_html = build_student_details_html(data, frm.doc.fee_month);
					let fees_paid_html = build_fees_paid_details_html(data);
					
					frm.fields_dict.student_html.$wrapper.html(student_html);
					if (frm.fields_dict.fees_paid_details_html) {
						frm.fields_dict.fees_paid_details_html.$wrapper.html(fees_paid_html);
					}
				}
			}
		});
	},
	monthly_fee: function(frm) {
		calculate_totals(frm);
	},
	add_discount: function(frm) {
		if (!frm.doc.add_discount) {
			frm.set_value('discount_amount', 0);
		}
		calculate_totals(frm);
	},
	discount_amount: function(frm) {
		calculate_totals(frm);
	},
	apply_gst_18: function(frm) {
		calculate_totals(frm);
	},
	paid_amount: function(frm) {
		calculate_totals(frm);
	},
	outstanding_amount: function(frm) {
		calculate_totals(frm);
	}
});

frappe.ui.form.on("Fees Invoice Details", {
	month: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.month) {
			let amount = get_row_amount(frm, row.month);
			frappe.model.set_value(cdt, cdn, 'amount_need_to_pay', amount);
			frappe.model.set_value(cdt, cdn, 'paid_amount', amount);
		}
		update_monthly_fee_from_details(frm);
	},
	paid_amount: function(frm, cdt, cdn) {
		update_monthly_fee_from_details(frm);
	}
});

// What a fresh row for this month should be billed -- the server works this out
// per student (starting payment still pending, pro-rated joining month, or the
// plain monthly fee) and caches it in student_detail_json.
function get_row_amount(frm, month) {
	if (!frm.doc.student_detail_json) return 0;

	let data = JSON.parse(frm.doc.student_detail_json);
	let amounts = data.row_amounts || {};

	if (month in amounts) return amounts[month];
	return month === "Starting Payment" ? (data.starting_payment || 0) : (data.monthly_fee || 0);
}

function get_selected_coupons(frm) {
	return (frm.doc.coupon__code || "").split(",").map(c => c.trim()).filter(Boolean);
}

// Picker for the student's redeemable referral coupons. Multiple coupons are
// stored on the invoice as a comma separated list and their amounts added up.
function show_coupon_dialog(frm, coupons) {
	let already_applied = get_selected_coupons(frm);
	let by_code = {};
	coupons.forEach(c => { by_code[c.coupon_code] = c; });

	let dialog = new frappe.ui.Dialog({
		title: __("Available Coupons"),
		fields: [
			{
				fieldtype: "MultiCheck",
				fieldname: "coupons",
				label: __("Pick the coupons to use on this invoice"),
				columns: 1,
				select_all: coupons.length > 1,
				sort_options: false,
				options: coupons.map(c => ({
					label: `<b>${c.coupon_code}</b> &nbsp;&mdash;&nbsp; ${format_currency(c.amount)}`
						+ (c.valid_till ? ` <span class="text-muted">(${__("valid till")} ${frappe.datetime.str_to_user(c.valid_till)})</span>` : ""),
					value: c.coupon_code,
					checked: already_applied.includes(c.coupon_code)
				})),
				on_change: () => update_coupon_dialog_total()
			},
			{ fieldtype: "HTML", fieldname: "coupon_total" }
		],
		primary_action_label: __("Apply"),
		primary_action() {
			let picked = dialog.get_value("coupons") || [];
			let total = picked.reduce((sum, code) => sum + (by_code[code] || {}).amount, 0);

			if (total > (frm.doc.paid_amount || 0)) {
				frappe.msgprint({
					title: __("Coupon Too Large"),
					message: __("The selected coupons come to {0}, which is more than the Paid Amount of {1}.",
						[format_currency(total), format_currency(frm.doc.paid_amount || 0)]),
					indicator: "red"
				});
				return;
			}

			// Stored without spaces -- the server matches a single code against
			// this list with find_in_set().
			frm.set_value("coupon__code", picked.join(","));
			frm.set_value("coupon_amount", total);
			dialog.hide();

			if (picked.length) {
				frappe.show_alert({
					message: __("{0} applied. Cash to collect is now {1}.",
						[picked.join(", "), format_currency((frm.doc.paid_amount || 0) - total)]),
					indicator: "green"
				}, 10);
			} else {
				frappe.show_alert({ message: __("Coupons removed."), indicator: "orange" }, 5);
			}
		},
		secondary_action_label: __("Cancel")
	});

	function update_coupon_dialog_total() {
		let picked = dialog.get_value("coupons") || [];
		let total = picked.reduce((sum, code) => sum + (by_code[code] || {}).amount, 0);
		let paid = frm.doc.paid_amount || 0;
		let over = total > paid;

		dialog.fields_dict.coupon_total.$wrapper.html(`
			<div style="padding:12px;border-radius:8px;background:${over ? "#fee2e2" : "#eff6ff"};color:${over ? "#991b1b" : "#1e3a8a"};font-size:13px;">
				<div>${__("Coupon total")}: <b>${format_currency(total)}</b>
					&nbsp;/&nbsp; ${__("Paid Amount")}: <b>${format_currency(paid)}</b></div>
				<div style="margin-top:6px;font-size:15px;">
					${over
						? __("Coupons exceed the Paid Amount.")
						: `${__("Cash to collect")}: <b style="font-size:18px;">${format_currency(paid - total)}</b>`}
				</div>
			</div>`);
	}

	dialog.show();
	update_coupon_dialog_total();
}

// Pre-submit recap of what the cashier should have in hand: every row, what it
// was billed, what is being recorded as paid, and where the two do not match.
function build_collection_summary_html(frm) {
	let rows = (frm.doc.fees_details || []).filter(row => row.month);
	let billed = 0;
	let paid = 0;
	let partial_months = [];

	let row_html = rows.map(row => {
		let need = row.amount_need_to_pay || 0;
		let got = row.paid_amount || 0;
		billed += need;
		paid += got;

		let short = need - got;
		let note = "";
		if (short > 0) {
			partial_months.push(row.month);
			note = `<span style="color:#b91c1c;">${__("Short by")} ${format_currency(short)}</span>`;
		} else {
			note = `<span style="color:#065f46;">${__("Full")}</span>`;
		}

		return `<tr>
			<td>${row.month}</td>
			<td class="text-right">${format_currency(need)}</td>
			<td class="text-right"><b>${format_currency(got)}</b></td>
			<td class="text-right">${note}</td>
		</tr>`;
	}).join("");

	if (!rows.length) {
		row_html = `<tr><td colspan="4" class="text-muted">${__("No rows in Fees Details.")}</td></tr>`;
	}

	// The coupon is a credit against the payment, so the months are recorded as
	// fully paid and only the difference comes in as cash.
	let coupon_codes = get_selected_coupons(frm);
	let coupon = frm.doc.coupon_amount || 0;
	let cash = Math.max(0, paid - coupon);
	let coupon_html = "";

	if (coupon_codes.length) {
		coupon_html = `<div style="margin-top:12px;padding:10px 12px;border-radius:6px;background:#f5f3ff;color:#5b21b6;">
			${__("Coupon")} <b>${coupon_codes.join(", ")}</b>
			${__("covers")} <b>${format_currency(coupon)}</b> ${__("of the Paid Amount")}
			&mdash; ${__("these coupons will be marked used and cannot be applied again.")}
		</div>`;
	}

	let warnings = "";

	if (paid <= 0) {
		warnings += `<div style="margin-top:12px;padding:10px 12px;border-radius:6px;background:#fef3c7;color:#92400e;">
			${__("Paid Amount is zero. Nothing will be recorded as collected for this student.")}
		</div>`;
	} else if (partial_months.length) {
		warnings += `<div style="margin-top:12px;padding:10px 12px;border-radius:6px;background:#fef3c7;color:#92400e;">
			${__("Part payment for {0}. The remaining {1} stays pending on the student.", [partial_months.join(", "), format_currency(billed - paid)])}
		</div>`;
	}

	// The starting payment settles two months in advance: the first full month
	// once half of it is in, the last month only once all of it is. Below that
	// the last month is merely reserved -- worth spelling out before the money
	// is committed.
	let starting_row = rows.find(row => row.month === "Starting Payment");
	if (starting_row && frm.doc.student_detail_json) {
		let advance_months = JSON.parse(frm.doc.student_detail_json).advance_months || [];
		let [first_month, last_month] = advance_months;

		if (first_month) {
			let billed = starting_row.amount_need_to_pay || 0;
			let percent = billed ? ((starting_row.paid_amount || 0) / billed) * 100 : 0;
			let message, background, colour;

			if (percent >= 100) {
				background = "#d1fae5"; colour = "#065f46";
				message = last_month
					? __("Starting payment is being paid in full, so {0} and {1} will be marked Paid by Starting Payment.", [first_month, last_month])
					: __("Starting payment is being paid in full, so {0} will be marked Paid by Starting Payment.", [first_month]);
			} else if (percent >= 50) {
				background = "#e0f2fe"; colour = "#075985";
				message = last_month
					? __("Half the starting payment is in, so {0} will be marked Paid by Starting Payment and {1} will be Reserved — still due.", [first_month, last_month])
					: __("Half the starting payment is in, so {0} will be marked Paid by Starting Payment.", [first_month]);
			} else {
				background = "#fef3c7"; colour = "#92400e";
				message = __("Less than half the starting payment is in, so {0} will not be settled yet.", [advance_months.join(", ")]);
			}

			warnings += `<div style="margin-top:12px;padding:10px 12px;border-radius:6px;background:${background};color:${colour};">
				${message}
			</div>`;
		}
	}

	return `
	<div style="font-size:13px;">
		<p style="margin-bottom:12px;">
			${__("Check the Paid Amount against the money actually collected. Once submitted this posts against the student's fee record and can only be reversed by cancelling.")}
		</p>
		<table class="table table-bordered" style="margin-bottom:0;">
			<thead>
				<tr>
					<th>${__("Month")}</th>
					<th class="text-right">${__("Need to Pay")}</th>
					<th class="text-right">${__("Paid")}</th>
					<th class="text-right">${__("Status")}</th>
				</tr>
			</thead>
			<tbody>${row_html}</tbody>
			<tfoot>
				<tr style="background:#f9fafb;">
					<th>${__("Total")}</th>
					<th class="text-right">${format_currency(billed)}</th>
					<th class="text-right">${format_currency(paid)}</th>
					<th></th>
				</tr>
			</tfoot>
		</table>
		${coupon_html}
		<div style="margin-top:14px;padding:12px;border-radius:8px;background:#eff6ff;color:#1e3a8a;font-size:15px;">
			${__("Collect")} <b style="font-size:18px;">${format_currency(cash)}</b>
			${frm.doc.payment_method ? ` ${__("by")} <b>${frm.doc.payment_method}</b>` : ""}
		</div>
		${warnings}
	</div>`;
}

function update_monthly_fee_from_details(frm) {
	let total_fee = 0;
	let total_paid = 0;

	(frm.doc.fees_details || []).forEach(row => {
		if (!row.month) return;
		total_fee += (row.amount_need_to_pay || 0);
		total_paid += (row.paid_amount || 0);
	});

	frm.set_value("monthly_fee", total_fee);
	frm.set_value("paid_amount", total_paid);

	// Editing the rows down can leave the coupon worth more than the payment it
	// is meant to credit -- say so here rather than at submit.
	if ((frm.doc.coupon_amount || 0) > total_paid) {
		frappe.show_alert({
			message: __("Coupon of {0} is now more than the Paid Amount of {1}. Reopen Add Coupon to change it.",
				[format_currency(frm.doc.coupon_amount), format_currency(total_paid)]),
			indicator: "red"
		}, 10);
	}

	calculate_totals(frm);
}

function calculate_totals(frm) {
	let monthly_fee = frm.doc.monthly_fee || 0;
	let discount = frm.doc.add_discount ? (frm.doc.discount_amount || 0) : 0;
	
	let net_total = monthly_fee - discount;
	let gst_amount = 0;
	
	if (frm.doc.apply_gst_18) {
		gst_amount = net_total * 0.18;
	}
	
	frm.set_value('gst_amount', gst_amount);
	
	let grand_total = net_total + gst_amount;
	frm.set_value('grand_total', grand_total);
	
	let outstanding = frm.doc.outstanding_amount || 0;
	let final_total = grand_total + outstanding;
	let balance = Math.max(0, final_total - (frm.doc.paid_amount || 0));
	frm.set_value('balance_amount', balance);
}

function get_shared_styles() {
	return `
<style>
	.sft-container {
		font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		color: #333;
		padding: 24px 0;
	}

	/* Student Card */
	.sft-student-card {
		display: flex;
		align-items: center;
		background: #ffffff;
		border-radius: 16px;
		padding: 24px;
		box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
		border: 1px solid #f3f4f6;
		margin-bottom: 24px;
		gap: 24px;
	}
	.sft-student-img {
		width: 90px;
		height: 90px;
		border-radius: 50%;
		object-fit: cover;
		background-color: #e5e7eb;
		border: 4px solid #f3f4f6;
		flex-shrink: 0;
	}
	.sft-student-info { flex: 1; }
	.sft-student-name {
		font-size: 22px;
		font-weight: 700;
		color: #111827;
		margin: 0 0 10px 0;
	}
	.sft-student-meta {
		display: flex;
		gap: 24px;
		flex-wrap: wrap;
	}
	.sft-meta-item { display: flex; flex-direction: column; }
	.sft-meta-label {
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #9ca3af;
		font-weight: 600;
		margin-bottom: 3px;
	}
	.sft-meta-value {
		font-size: 14px;
		color: #374151;
		font-weight: 600;
	}

	/* Summary + Legend Row */
	.sft-summary-row {
		display: flex;
		justify-content: space-between;
		align-items: stretch;
		margin-bottom: 24px;
		gap: 16px;
		flex-wrap: wrap;
	}
	.sft-summary-box { display: flex; gap: 12px; }
	.sft-stat-card {
		background: #fff;
		padding: 14px 22px;
		border-radius: 12px;
		box-shadow: 0 1px 3px rgba(0,0,0,0.05);
		border: 1px solid #e5e7eb;
		text-align: center;
		min-width: 100px;
	}
	.sft-stat-val {
		font-size: 22px;
		font-weight: 700;
	}
	.sft-stat-val.green { color: #10b981; }
	.sft-stat-val.red { color: #ef4444; }
	.sft-stat-val.orange { color: #f59e0b; }
	.sft-stat-label {
		font-size: 11px;
		color: #6b7280;
		font-weight: 600;
		text-transform: uppercase;
		margin-top: 2px;
	}
	.sft-legend {
		display: flex;
		gap: 14px;
		background: #fff;
		padding: 14px 20px;
		border-radius: 12px;
		box-shadow: 0 1px 3px rgba(0,0,0,0.05);
		border: 1px solid #e5e7eb;
		align-items: center;
		flex-wrap: wrap;
	}
	.sft-legend-item {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		color: #4b5563;
		font-weight: 500;
	}
	.sft-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
	.sft-dot-early { background-color: #10b981; }
	.sft-dot-late { background-color: #ef4444; }
	.sft-dot-unpaid { background-color: #fee2e2; border: 1px solid #f87171; }
	.sft-dot-notjoined { background-color: #d1d5db; }
	.sft-dot-startpay { background-color: #0ea5e9; }
	.sft-dot-reserved { background-color: #9ca3af; }

	/* Grid */
	.sft-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 16px;
	}
	@media (max-width: 1100px) { .sft-grid { grid-template-columns: repeat(3, 1fr); } }
	@media (max-width: 768px) {
		.sft-grid { grid-template-columns: repeat(2, 1fr); }
		.sft-student-card { flex-direction: column; text-align: center; }
		.sft-student-meta { justify-content: center; }
	}
	@media (max-width: 480px) { .sft-grid { grid-template-columns: 1fr; } }

	/* Month Cards */
	.sft-month-card {
		background: #fff;
		border-radius: 14px;
		padding: 18px;
		box-shadow: 0 1px 3px rgba(0,0,0,0.04);
		border: 1px solid #f3f4f6;
		transition: transform 0.2s ease, box-shadow 0.2s ease;
		position: relative;
		cursor: default;
	}
	.sft-month-card:hover {
		transform: translateY(-3px);
		box-shadow: 0 8px 16px -4px rgba(0,0,0,0.1);
	}
	.sft-mc-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 10px;
	}
	.sft-mc-month { font-size: 18px; font-weight: 700; color: #1f2937; }
	.sft-mc-icon {
		width: 28px; height: 28px;
		border-radius: 50%;
		display: flex; align-items: center; justify-content: center;
		font-size: 13px;
	}
	.sft-mc-status {
		display: inline-block;
		padding: 3px 10px;
		border-radius: 20px;
		font-size: 11px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		margin-bottom: 10px;
	}
	.sft-mc-details {
		font-size: 12px;
		color: #6b7280;
		display: flex; flex-direction: column; gap: 3px;
	}
	.sft-mc-details span { display: flex; align-items: center; gap: 5px; }

	/* Card status classes */
	.card-notjoined { background-color: #f9fafb; border-color: #e5e7eb; }
	.card-notjoined .sft-mc-month { color: #9ca3af; }
	.card-notjoined .sft-mc-status { background: #f3f4f6; color: #6b7280; }
	.card-notjoined .sft-mc-icon { background: #d1d5db; color: #fff; }
	
	.card-notpaid { background-color: #fffbfb; border-color: #fecaca; }
	.card-notpaid .sft-mc-status { background: #fee2e2; color: #b91c1c; }
	.card-notpaid .sft-mc-icon { background: #ef4444; color: #fff; }

	/* A paid month always reads as paid -- green. How late it was paid is
	   carried by the icon and the Paid Late tag, never by making a settled
	   month look like an unpaid one. */
	.card-early .sft-mc-status,
	.card-late .sft-mc-status { background: #d1fae5; color: #065f46; }

	.card-early .sft-mc-icon { background: #10b981; color: #fff; }
	.card-late .sft-mc-icon { background: #ef4444; color: #fff; }

	.card-late { border-color: #fecaca; background-color: #fffbfb; }

	.card-partial .sft-mc-status { background: #e0e7ff; color: #3730a3; }
	.card-partial .sft-mc-icon { background: #6366f1; color: #fff; }

	/* Settled out of the starting payment -- paid, but not paid for on its own */
	.card-startpay { background-color: #f0f9ff; border-color: #bae6fd; }
	.card-startpay .sft-mc-status { background: #e0f2fe; color: #075985; }
	.card-startpay .sft-mc-icon { background: #0ea5e9; color: #fff; }

	/* Held against the rest of the starting payment, still due -- greyed out */
	.card-reserved { background-color: #f9fafb; border-color: #e5e7eb; }
	.card-reserved .sft-mc-month { color: #6b7280; }
	.card-reserved .sft-mc-status { background: #e5e7eb; color: #4b5563; }
	.card-reserved .sft-mc-icon { background: #9ca3af; color: #fff; }
	.card-reserved .sft-mc-details { color: #9ca3af; }

	/* "Paid by Starting Payment" tag on a month card */
	.sft-mc-tag {
		display: inline-block;
		margin-bottom: 10px;
		padding: 2px 8px;
		border-radius: 20px;
		font-size: 10px;
		font-weight: 600;
		letter-spacing: 0.02em;
		background: #0ea5e9;
		color: #fff;
	}
	.sft-mc-tag.grey { background: #9ca3af; }
	.sft-mc-tag.red { background: #ef4444; }

	/* Tooltip */
	.sft-tooltip-text {
		visibility: hidden;
		width: max-content;
		background-color: #1f2937;
		color: #fff;
		text-align: center;
		border-radius: 6px;
		padding: 6px 12px;
		position: absolute;
		z-index: 1;
		bottom: calc(100% + 8px);
		left: 50%;
		transform: translateX(-50%);
		opacity: 0;
		transition: opacity 0.25s;
		font-size: 12px;
		font-weight: 500;
		white-space: nowrap;
		pointer-events: none;
	}
	.sft-tooltip-text::after {
		content: "";
		position: absolute;
		top: 100%;
		left: 50%;
		margin-left: -5px;
		border-width: 5px;
		border-style: solid;
		border-color: #1f2937 transparent transparent transparent;
	}
	.sft-month-card:hover .sft-tooltip-text {
		visibility: visible;
		opacity: 1;
	}
</style>`;
}

function build_student_details_html(data, fee_month) {
	const MONTHS = get_academic_month_list(data);

	// Build payment lookup
	let payDict = {};
	(data.payment_details || []).forEach(row => {
		payDict[row.month] = row;
	});

	let adAcIndex = get_admission_index(data, MONTHS);

	// Summary calculations
	let paid = 0, remaining = 0, late = 0;
	MONTHS.forEach((m, idx) => {
		let p = payDict[m];
		let status = 'Not Paid';
		if (p && p.status) {
			status = p.status;
		} else if (idx < adAcIndex) {
			status = 'Not Joined';
		}
		if (status === 'Paid' || status === PAID_BY_STARTING_PAYMENT) {
			paid++;
			// A month covered by the starting payment was never late in its own
			// right -- the money came in with the starting payment.
			if (status === 'Paid' && p && get_payment_timing(data, MONTHS, m, p.date).late) {
				late++;
			}
		} else if (status === 'Not Paid' || status === 'Partial' || status === RESERVED) {
			remaining++;
		}
	});

	let formatDate = (dateStr) => {
		if (!dateStr) return 'N/A';
		let d = new Date(dateStr);
		return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
	};

	let formatCurrency = (val) => {
		return '₹ ' + Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
	};

	let imgSrc = data.image || '/assets/frappe/images/default-avatar.png';

	let starting_row = payDict["Starting Payment"];
	let starting_paid = starting_row ? starting_row.amount_paid : 0;
	let starting_pending = starting_row ? starting_row.pending : (data.starting_payment || 0);

	// Which months the starting payment has actually settled, and which it is
	// only holding -- read straight off the statuses it wrote.
	let coveredMonths = (data.payment_details || [])
		.filter(row => row.status === PAID_BY_STARTING_PAYMENT && row.month !== 'Starting Payment')
		.map(row => row.month);
	let reservedMonths = (data.payment_details || [])
		.filter(row => row.status === RESERVED)
		.map(row => row.month);

	let startingCoverHtml = '';
	if (coveredMonths.length) {
		startingCoverHtml += `
			<div class="sft-meta-item">
				<span class="sft-meta-label" style="color: #6b7280;">Paid by Starting Payment</span>
				<span class="sft-mc-tag" style="margin-bottom: 0; align-self: flex-start;">${coveredMonths.join(', ')}</span>
			</div>`;
	}
	if (reservedMonths.length) {
		startingCoverHtml += `
			<div class="sft-meta-item">
				<span class="sft-meta-label" style="color: #6b7280;">Reserved</span>
				<span class="sft-mc-tag grey" style="margin-bottom: 0; align-self: flex-start;">${reservedMonths.join(', ')}</span>
			</div>`;
	}

	let startingPaymentHtml = '';
	if (data.starting_payment > 0) {
		startingPaymentHtml = `
		<div style="margin-top: 16px; padding-top: 16px; border-top: 1px dashed #e5e7eb; display: flex; gap: 24px; flex-wrap: wrap;">
			<div class="sft-meta-item">
				<span class="sft-meta-label" style="color: #6b7280;">Starting Amount</span>
				<span class="sft-meta-value" style="color: #374151; font-size: 15px;">${formatCurrency(data.starting_payment)}</span>
			</div>
			<div class="sft-meta-item">
				<span class="sft-meta-label" style="color: #6b7280;">Starting Paid</span>
				<span class="sft-meta-value" style="color: #10b981; font-size: 15px;">${formatCurrency(starting_paid)}</span>
			</div>
			${Number(starting_pending) > 0 ? `
			<div class="sft-meta-item">
				<span class="sft-meta-label" style="color: #6b7280;">Starting Pending</span>
				<span class="sft-meta-value" style="color: #ef4444; font-size: 15px;">${formatCurrency(starting_pending)}</span>
			</div>` : ``}
			${startingCoverHtml}
		</div>`;
	}

	let dueDateFormatted = '-';
	let dueDay = parseInt(data.fees_due_date, 10);
	if (dueDay) {
		dueDateFormatted = `${dueDay}${ordinal(dueDay)} of ${fee_month && fee_month !== 'Starting Payment' ? fee_month : 'every month'}`;
	}

	return `
${get_shared_styles()}
<div class="sft-container" style="padding-bottom: 0;">
	<!-- Student Card -->
	<div class="sft-student-card" style="margin-bottom: 24px;">
		<img src="${imgSrc}" alt="Student" class="sft-student-img" onerror="this.src='/assets/frappe/images/default-avatar.png'">
		<div class="sft-student-info">
			<h2 class="sft-student-name">${data.student_name || ''}</h2>
			<div class="sft-student-meta">
				<div class="sft-meta-item">
					<span class="sft-meta-label">Admission Date</span>
					<span class="sft-meta-value">${formatDate(data.admission_date)}</span>
				</div>
				<div class="sft-meta-item">
					<span class="sft-meta-label">Due Date</span>
					<span class="sft-meta-value" style="color: #ef4444;">${dueDateFormatted}</span>
				</div>
				<div class="sft-meta-item">
					<span class="sft-meta-label">Standard</span>
					<span class="sft-meta-value">${data.standard || '-'}</span>
				</div>
				<div class="sft-meta-item">
					<span class="sft-meta-label">Current Batch</span>
					<span class="sft-meta-value">${data.current_batch || '-'}</span>
				</div>
				<div class="sft-meta-item">
					<span class="sft-meta-label">Academic Year</span>
					<span class="sft-meta-value">${data.academic_year || 'Current'}</span>
				</div>
			</div>
			${startingPaymentHtml}
		</div>
	</div>

	<!-- Summary + Legend -->
	<div class="sft-summary-row" style="margin-bottom: 0;">
		<div class="sft-summary-box">
			<div class="sft-stat-card">
				<div class="sft-stat-val green">${paid}</div>
				<div class="sft-stat-label">Months Paid</div>
			</div>
			<div class="sft-stat-card">
				<div class="sft-stat-val red">${remaining}</div>
				<div class="sft-stat-label">Remaining</div>
			</div>
			<div class="sft-stat-card">
				<div class="sft-stat-val orange">${late}</div>
				<div class="sft-stat-label">Late Payments</div>
			</div>
		</div>
		<div class="sft-legend">
			<div class="sft-legend-item"><div class="sft-dot sft-dot-early"></div>Paid on time</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-late"></div>Paid late${dueDay ? ` (after the ${dueDay}${ordinal(dueDay)})` : ''}</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-unpaid"></div>Pending</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-startpay"></div>By Starting Payment</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-reserved"></div>Reserved</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-notjoined"></div>Not Joined</div>
		</div>
	</div>
</div>
`;
}

function build_fees_paid_details_html(data) {
	const MONTHS = get_academic_month_list(data);
	const SHORT = MONTH_SHORT;

	// Build payment lookup
	let payDict = {};
	(data.payment_details || []).forEach(row => {
		payDict[row.month] = row;
	});

	let adAcIndex = get_admission_index(data, MONTHS);

	let formatDate = (dateStr) => {
		if (!dateStr) return 'N/A';
		let d = new Date(dateStr);
		return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
	};

	// Build month cards
	let monthCardsHtml = '';
	MONTHS.forEach((m, idx) => {
		let p = payDict[m];
		let status = 'Not Paid';
		let pdDate = null;
		let cardClass = 'card-notpaid';
		let icon = '⏳';

		if (p && p.status) {
			status = p.status;
			pdDate = p.date;
		} else if (idx < adAcIndex) {
			status = 'Not Joined';
		}

		// Label shown on the status pill. The starting payment statuses read as
		// plain Paid / Reserved on the card, with the tag below carrying the
		// "where the money came from" part.
		let statusLabel = status;
		let timing = get_payment_timing(data, MONTHS, m, pdDate);
		let lateText = timing.days
			? `${timing.days} ${timing.days === 1 ? 'day' : 'days'} late`
			: 'Paid late';

		if (status === 'Not Joined') {
			cardClass = 'card-notjoined';
			icon = '🚫';
		} else if (status === PAID_BY_STARTING_PAYMENT) {
			cardClass = 'card-startpay';
			icon = '★';
			statusLabel = 'Paid';
		} else if (status === RESERVED) {
			cardClass = 'card-reserved';
			icon = '🔒';
		} else if (status === 'Paid') {
			cardClass = timing.late ? 'card-late' : 'card-early';
			icon = timing.late ? '⏰' : '✔';
		} else if (status === 'Partial') {
			cardClass = 'card-partial';
			icon = '◐';
		}

		let tagHtml = '';
		if (status === PAID_BY_STARTING_PAYMENT) {
			tagHtml = `<div class="sft-mc-tag">Paid by Starting Payment</div>`;
		} else if (status === RESERVED) {
			tagHtml = `<div class="sft-mc-tag grey">Reserved by Starting Payment</div>`;
		} else if (status === 'Paid' && timing.late) {
			tagHtml = `<div class="sft-mc-tag red">⏰ ${lateText}</div>`;
		}

		let tooltipHtml = '';
		if (pdDate && status === 'Paid' && timing.late) {
			tooltipHtml = `<div class="sft-tooltip-text">Due ${data.fees_due_date}${ordinal(data.fees_due_date)} ${m} — paid ${formatDate(pdDate)}${timing.days ? ` (${lateText})` : ''}</div>`;
		} else if (pdDate && (status === 'Paid' || status === 'Partial')) {
			tooltipHtml = `<div class="sft-tooltip-text">Paid on ${formatDate(pdDate)}</div>`;
		} else if (status === PAID_BY_STARTING_PAYMENT) {
			tooltipHtml = `<div class="sft-tooltip-text">Settled out of the Starting Payment</div>`;
		} else if (status === RESERVED) {
			tooltipHtml = `<div class="sft-tooltip-text">Held against the rest of the Starting Payment — still due</div>`;
		}

		let formatCurrency = (val) => {
			return '₹ ' + Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
		};

		let admission = parse_iso_date(data.admission_date);
		let is_joining_month = admission && MONTH_NAMES[admission.month - 1] === m;

		let detailLines = '';
		if (status !== 'Not Joined') {
			detailLines += `<span>🏠 ${data.current_batch || '-'}</span>`;
		}
		if (is_joining_month && status !== 'Not Joined') {
			detailLines += `<span style="color:#6b7280;">🎓 Joined ${formatDate(data.admission_date)}</span>`;
		}
		if ((status === 'Paid' || status === 'Partial') && pdDate) {
			detailLines += `<span>📅 ${formatDate(pdDate)}</span>`;
			if (status === 'Paid' && timing.late && data.fees_due_date) {
				detailLines += `<span style="color:#b91c1c;">⏰ Due ${data.fees_due_date}${ordinal(data.fees_due_date)} ${m}</span>`;
			}
		} else if (status === 'Not Paid') {
			detailLines += `<span>⚠️ Payment Pending</span>`;
		} else if (status === PAID_BY_STARTING_PAYMENT) {
			detailLines += `<span>★ No separate payment due</span>`;
		} else if (status === RESERVED && p) {
			detailLines += `<span>⚠️ ${formatCurrency(p.pending)} still due</span>`;
		} else if (status === 'Not Joined') {
			detailLines += `<span>—</span>`;
		}
		if ((status === 'Paid' || status === 'Partial') && p) {
			detailLines += `<span>💰 ${formatCurrency(p.amount_paid)}</span>`;
		}

		monthCardsHtml += `
			<div class="sft-month-card ${cardClass}">
				${tooltipHtml}
				<div class="sft-mc-header">
					<div class="sft-mc-month">${SHORT[m]}</div>
					<div class="sft-mc-icon">${icon}</div>
				</div>
				<div class="sft-mc-status">${statusLabel}</div>
				${tagHtml}
				<div class="sft-mc-details">${detailLines}</div>
			</div>
		`;
	});

	return `
${get_shared_styles()}
<div class="sft-container" style="padding-top: 0;">
	<!-- Month Grid -->
	<div class="sft-grid">
		${monthCardsHtml}
	</div>
</div>
`;
}



// "Generate Bill" -- pick the parent to notify, then hand the payment
// confirmation to WhatsApp with a link to the bill PDF.
function generate_bill(frm) {
	frappe.dom.freeze(__("Preparing the bill..."));

	frappe.call({
		method: "bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice.get_whatsapp_bill",
		args: { invoice: frm.doc.name },
		always: () => frappe.dom.unfreeze(),
		callback: function(r) {
			if (!r.message) return;
			show_whatsapp_bill_dialog(frm, r.message);
		}
	});
}

function show_whatsapp_bill_dialog(frm, bill) {
	let contacts = bill.contacts || [];

	if (!contacts.length) {
		frappe.msgprint({
			title: __("No Mobile Number"),
			message: __("Neither a father nor a mother mobile number is on record for {0}. Add one on the Student first.",
				[frm.doc.student_name || frm.doc.student]),
			indicator: "orange"
		});
		return;
	}

	// The student's Preferred Mobile Number decides what the dialog opens on.
	let preferred = contacts.find(c => c.preferred) || contacts[0];

	let dialog = new frappe.ui.Dialog({
		title: __("Send Bill on WhatsApp"),
		fields: [
			{
				fieldtype: "Select",
				fieldname: "contact",
				label: __("Send to"),
				reqd: 1,
				default: preferred.parent,
				options: contacts.map(c => ({
					label: `${c.label}${c.name ? " — " + c.name : ""} (${c.raw})`,
					value: c.parent
				}))
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Data",
				fieldname: "custom_number",
				label: __("Or another number"),
				description: __("Leave blank to use the number picked above.")
			},
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Small Text",
				fieldname: "message",
				label: __("Message"),
				default: bill.message,
				reqd: 1
			},
			{
				fieldtype: "HTML",
				fieldname: "bill_note",
				options: bill.bill_url
					? `<div style="padding:10px 12px;border-radius:6px;background:#eff6ff;color:#1e3a8a;font-size:13px;">
							${__("The bill PDF goes across as a link in the message")} &mdash;
							<a href="${bill.bill_url}" target="_blank">${__("preview it")}</a>.
							${__("WhatsApp cannot take a file attachment from a web link, so attach the PDF by hand if a copy in the chat is needed.")}
						</div>`
					: `<div style="padding:10px 12px;border-radius:6px;background:#fef3c7;color:#92400e;font-size:13px;">
							${__("The bill PDF could not be generated, so the message goes without a link.")}
						</div>`
			}
		],
		primary_action_label: __("Open WhatsApp"),
		primary_action(values) {
			let picked = contacts.find(c => c.parent === values.contact) || preferred;
			let number = (values.custom_number || "").replace(/\D/g, "") || picked.number;

			if (!number) {
				frappe.msgprint(__("That number has no digits to dial."));
				return;
			}
			// A bare 10 digit number typed in here still needs the country code.
			if (number.length === 10) number = "91" + number;

			dialog.hide();
			window.open(`https://wa.me/${number}?text=${encodeURIComponent(values.message)}`, "_blank");
		},
		secondary_action_label: __("Cancel")
	});

	dialog.show();
	dialog.$wrapper.find('[data-fieldname="message"] textarea').css({ "min-height": "260px", "font-size": "12px" });
}
