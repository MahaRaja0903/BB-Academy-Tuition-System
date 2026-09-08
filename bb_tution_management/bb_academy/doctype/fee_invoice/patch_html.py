import re

with open('fee_invoice.js', 'r') as f:
    content = f.read()

old_html_func = """function build_collection_summary_html(frm) {
	let rows = (frm.doc.fees_details || []).filter(row => row.month);
	let billed = 0;
	let paid = 0;
	let partial_months = [];

	let student_name = frm.doc.student_name || frm.doc.student || "N/A";
	let standard = frm.doc.standard || "N/A";
	let batch = frm.doc.current_batch || "N/A";
	let student_details_html = `<div style="margin-bottom:12px;padding:10px 12px;border-radius:6px;background:#f9fafb;border:1px solid #e5e7eb;">
		<strong>Student:</strong> ${student_name}<br>
		<strong>Standard:</strong> ${standard}<br>
		<strong>Batch:</strong> ${batch}
	</div>`;

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
			${__("covers")} <b>${format_currency(coupon)}</b> ${__("of the Total Paid Amount")}
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
			${__("Check the Total Paid amount (Cash + Coupon) against what is being credited. Once submitted this posts against the student's fee record.")}
		</p>
		${student_details_html}
		<table class="table table-bordered" style="margin-bottom:0;">
			<thead>
				<tr>
					<th>${__("Month")}</th>
					<th class="text-right">${__("Need to Pay")}</th>
					<th class="text-right">${__("Paid (Cash + Coupon)")}</th>
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
}"""

new_html_func = """function build_collection_summary_html(frm) {
	let rows = (frm.doc.fees_details || []).filter(row => row.month);
	let billed = 0;
	let paid = 0;
	let partial_months = [];

	let student_name = frm.doc.student_name || frm.doc.student || "N/A";
	let standard = "N/A";
	let batch = "N/A";
	
	if (frm.doc.student_detail_json) {
		try {
			let details = JSON.parse(frm.doc.student_detail_json);
			standard = details.standard || "N/A";
			batch = details.current_batch || "N/A";
		} catch (e) {}
	}
	if (standard === "N/A" && frm.doc.standard) standard = frm.doc.standard;
	if (batch === "N/A" && frm.doc.current_batch) batch = frm.doc.current_batch;

	let student_details_html = `<div style="margin-bottom:12px;padding:10px 12px;border-radius:6px;background:#f9fafb;border:1px solid #e5e7eb;">
		<strong>Student:</strong> ${student_name}<br>
		<strong>Standard:</strong> ${standard}<br>
		<strong>Batch:</strong> ${batch}
	</div>`;

	let coupon_remaining = frm.doc.coupon_amount || 0;
	let row_html = rows.map(row => {
		let need = row.amount_need_to_pay || 0;
		let got = row.paid_amount || 0;
		billed += need;
		paid += got;

		let short = need - got;
		let note = "";
		if (short > 0) {
			if (coupon_remaining >= short) {
				note = `<span style="color:#5b21b6;">${__("Coupon")} ${format_currency(short)}</span>`;
				coupon_remaining -= short;
			} else if (coupon_remaining > 0) {
				let actual_short = short - coupon_remaining;
				note = `<span style="color:#5b21b6;">${__("Coupon")} ${format_currency(coupon_remaining)}</span>, <span style="color:#b91c1c;">${__("Short by")} ${format_currency(actual_short)}</span>`;
				partial_months.push(row.month);
				coupon_remaining = 0;
			} else {
				partial_months.push(row.month);
				note = `<span style="color:#b91c1c;">${__("Short by")} ${format_currency(short)}</span>`;
			}
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

	let cash = paid;
	let coupon_codes = get_selected_coupons(frm);
	let total_coupon = frm.doc.coupon_amount || 0;
	let coupon_html = "";

	if (coupon_codes.length) {
		coupon_html = `<div style="margin-top:12px;padding:10px 12px;border-radius:6px;background:#f5f3ff;color:#5b21b6;">
			${__("Coupon")} <b>${coupon_codes.join(", ")}</b>
			${__("covers")} <b>${format_currency(total_coupon)}</b> ${__("of the remaining balance")}
			&mdash; ${__("these coupons will be marked used and cannot be applied again.")}
		</div>`;
	}

	let warnings = "";

	if (paid <= 0 && total_coupon <= 0) {
		warnings += `<div style="margin-top:12px;padding:10px 12px;border-radius:6px;background:#fef3c7;color:#92400e;">
			${__("Paid Amount is zero. Nothing will be recorded as collected for this student.")}
		</div>`;
	} else if (partial_months.length) {
		warnings += `<div style="margin-top:12px;padding:10px 12px;border-radius:6px;background:#fef3c7;color:#92400e;">
			${__("Part payment for {0}. The remaining {1} stays pending on the student.", [partial_months.join(", "), format_currency(billed - paid - total_coupon)])}
		</div>`;
	}

	let starting_row = rows.find(row => row.month === "Starting Payment");
	if (starting_row && frm.doc.student_detail_json) {
		let advance_months = JSON.parse(frm.doc.student_detail_json).advance_months || [];
		let [first_month, last_month] = advance_months;

		if (first_month) {
			let billed = starting_row.amount_need_to_pay || 0;
			// Use the total credit applied to this row for percentage calculation
			let total_row_credit = starting_row.paid_amount || 0;
			let shortfall = billed - total_row_credit;
			let row_coupon = Math.min(Math.max(0, shortfall), total_coupon);
			total_row_credit += row_coupon;

			let percent = billed ? (total_row_credit / billed) * 100 : 0;
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
			${__("Check the Paid Amount against the money actually collected. Once submitted this posts against the student's fee record.")}
		</p>
		${student_details_html}
		<table class="table table-bordered" style="margin-bottom:0;">
			<thead>
				<tr>
					<th>${__("Month")}</th>
					<th class="text-right">${__("Need to Pay")}</th>
					<th class="text-right">${__("Paid Amount")}</th>
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
}"""
content = content.replace(old_html_func, new_html_func)

with open('fee_invoice.js', 'w') as f:
    f.write(content)
