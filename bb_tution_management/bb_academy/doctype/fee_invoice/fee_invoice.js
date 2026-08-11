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
		// Render student fee tracking on refresh if student is set
		if (frm.doc.student) {
			frm.trigger("render_fee_tracking");
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

	// The starting payment settles two months in advance, but only once it is
	// paid in full -- worth spelling out before the money is committed.
	let starting_row = rows.find(row => row.month === "Starting Payment");
	if (starting_row && frm.doc.student_detail_json) {
		let advance = (JSON.parse(frm.doc.student_detail_json).advance_months || []).join(", ");
		if (advance) {
			let full = (starting_row.paid_amount || 0) >= (starting_row.amount_need_to_pay || 0);
			warnings += `<div style="margin-top:12px;padding:10px 12px;border-radius:6px;background:${full ? "#d1fae5" : "#e0e7ff"};color:${full ? "#065f46" : "#3730a3"};">
				${full
					? __("Starting payment is being paid in full, so {0} will be marked Paid.", [advance])
					: __("Starting payment is not being paid in full, so {0} will not be settled yet.", [advance])}
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
	.sft-dot-mid { background-color: #f59e0b; }
	.sft-dot-late { background-color: #ef4444; }
	.sft-dot-unpaid { background-color: #fee2e2; border: 1px solid #f87171; }
	.sft-dot-notjoined { background-color: #d1d5db; }

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

	.card-early .sft-mc-status { background: #d1fae5; color: #065f46; }
	.card-early .sft-mc-icon { background: #10b981; color: #fff; }

	.card-mid .sft-mc-status { background: #fef3c7; color: #92400e; }
	.card-mid .sft-mc-icon { background: #f59e0b; color: #fff; }

	.card-late .sft-mc-status { background: #fee2e2; color: #991b1b; }
	.card-late .sft-mc-icon { background: #ef4444; color: #fff; }

	.card-partial .sft-mc-status { background: #e0e7ff; color: #3730a3; }
	.card-partial .sft-mc-icon { background: #6366f1; color: #fff; }

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
	const MONTHS = ['April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'January', 'February', 'March'];
	
	// Build payment lookup
	let payDict = {};
	(data.payment_details || []).forEach(row => {
		payDict[row.month] = row;
	});

	// Calculate admission academic index (April=0 ... March=11)
	let adAcIndex = 0;
	if (data.admission_date) {
		let adDate = new Date(data.admission_date);
		let m = adDate.getMonth() + 1; // 1-12
		adAcIndex = m >= 4 ? m - 4 : m + 8;
	}

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
		if (status === 'Paid') {
			paid++;
			if (p && p.date) {
				let d = new Date(p.date).getDate();
				if (d > 15) late++;
			}
		} else if (status === 'Not Paid' || status === 'Partial') {
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
			<div class="sft-meta-item">
				<span class="sft-meta-label" style="color: #6b7280;">Starting Pending</span>
				<span class="sft-meta-value" style="color: #ef4444; font-size: 15px;">${formatCurrency(starting_pending)}</span>
			</div>
		</div>`;
	}

	let dueDateFormatted = '-';
	if (data.fees_due_date) {
		let day = parseInt(data.fees_due_date, 10);
		if (day) {
			let suffix = 'th';
			if (day === 1 || day === 21 || day === 31) suffix = 'st';
			else if (day === 2 || day === 22) suffix = 'nd';
			else if (day === 3 || day === 23) suffix = 'rd';
			dueDateFormatted = `${day}${suffix} of ${fee_month && fee_month !== 'Starting Payment' ? fee_month : 'every month'}`;
		}
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
			<div class="sft-legend-item"><div class="sft-dot sft-dot-early"></div>Early (&lt;10th)</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-mid"></div>Mid (10–15)</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-late"></div>Late (&gt;15th)</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-unpaid"></div>Pending</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-notjoined"></div>Not Joined</div>
		</div>
	</div>
</div>
`;
}

function build_fees_paid_details_html(data) {
	const MONTHS = ['April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'January', 'February', 'March'];
	const SHORT = { April: 'Apr', May: 'May', June: 'Jun', July: 'Jul', August: 'Aug', September: 'Sep', October: 'Oct', November: 'Nov', December: 'Dec', January: 'Jan', February: 'Feb', March: 'Mar' };

	// Build payment lookup
	let payDict = {};
	(data.payment_details || []).forEach(row => {
		payDict[row.month] = row;
	});

	// Calculate admission academic index (April=0 ... March=11)
	let adAcIndex = 0;
	if (data.admission_date) {
		let adDate = new Date(data.admission_date);
		let m = adDate.getMonth() + 1; // 1-12
		adAcIndex = m >= 4 ? m - 4 : m + 8;
	}

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

		if (status === 'Not Joined') {
			cardClass = 'card-notjoined';
			icon = '🚫';
		} else if (status === 'Paid') {
			icon = '✔';
			if (pdDate) {
				let d = new Date(pdDate).getDate();
				if (d < 10) cardClass = 'card-early';
				else if (d <= 15) cardClass = 'card-mid';
				else cardClass = 'card-late';
			} else {
				cardClass = 'card-early';
			}
		} else if (status === 'Partial') {
			cardClass = 'card-partial';
			icon = '◐';
		}

		let tooltipHtml = '';
		if (pdDate && (status === 'Paid' || status === 'Partial')) {
			tooltipHtml = `<div class="sft-tooltip-text">Paid on ${formatDate(pdDate)}</div>`;
		}

		let formatCurrency = (val) => {
			return '₹ ' + Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
		};

		let detailLines = '';
		if (status !== 'Not Joined') {
			detailLines += `<span>🏠 ${data.current_batch || '-'}</span>`;
		}
		if ((status === 'Paid' || status === 'Partial') && pdDate) {
			detailLines += `<span>📅 ${formatDate(pdDate)}</span>`;
		} else if (status === 'Not Paid') {
			detailLines += `<span>⚠️ Payment Pending</span>`;
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
				<div class="sft-mc-status">${status}</div>
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

