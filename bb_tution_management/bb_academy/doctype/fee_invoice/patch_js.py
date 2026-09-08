import re

with open('fee_invoice.js', 'r') as f:
    content = f.read()

# Update update_coupon_dialog_total
old_coupon_dialog = """	function update_coupon_dialog_total() {
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
	}"""
new_coupon_dialog = """	function update_coupon_dialog_total() {
		let picked = dialog.get_value("coupons") || [];
		let total = picked.reduce((sum, code) => sum + (by_code[code] || {}).amount, 0);
		let billed = frm.doc.grand_total || frm.doc.monthly_fee || 0;
		let over = total > billed;

		dialog.fields_dict.coupon_total.$wrapper.html(`
			<div style="padding:12px;border-radius:8px;background:${over ? "#fee2e2" : "#eff6ff"};color:${over ? "#991b1b" : "#1e3a8a"};font-size:13px;">
				<div>${__("Coupon total")}: <b>${format_currency(total)}</b>
					&nbsp;/&nbsp; ${__("Grand Total")}: <b>${format_currency(billed)}</b></div>
				<div style="margin-top:6px;font-size:15px;">
					${over
						? __("Coupons exceed the Grand Total.")
						: ""}
				</div>
			</div>`);
	}"""
content = content.replace(old_coupon_dialog, new_coupon_dialog)

# Update add_coupon error condition
old_add_coupon = """			if (total > (frm.doc.paid_amount || 0)) {
				frappe.msgprint({
					title: __("Coupon Too Large"),
					message: __("The selected coupons come to {0}, which is more than the Paid Amount of {1}.",
						[format_currency(total), format_currency(frm.doc.paid_amount || 0)]),
					indicator: "red"
				});
				return;
			}"""
new_add_coupon = """			let billed = frm.doc.grand_total || frm.doc.monthly_fee || 0;
			if (total > billed) {
				frappe.msgprint({
					title: __("Coupon Too Large"),
					message: __("The selected coupons come to {0}, which is more than the Grand Total of {1}.",
						[format_currency(total), format_currency(billed)]),
					indicator: "red"
				});
				return;
			}"""
content = content.replace(old_add_coupon, new_add_coupon)

old_add_coupon_success = """			if (picked.length) {
				frappe.show_alert({
					message: __("{0} applied. Cash to collect is now {1}.",
						[picked.join(", "), format_currency((frm.doc.paid_amount || 0) - total)]),
					indicator: "green"
				}, 10);
			} else {"""
new_add_coupon_success = """			if (picked.length) {
				frappe.show_alert({
					message: __("{0} applied.", [picked.join(", ")]),
					indicator: "green"
				}, 10);
			} else {"""
content = content.replace(old_add_coupon_success, new_add_coupon_success)

# Update update_monthly_fee_from_details
old_update_monthly = """	if ((frm.doc.coupon_amount || 0) > total_paid) {
		frappe.show_alert({
			message: __("Coupon of {0} is now more than the Paid Amount of {1}. Reopen Add Coupon to change it.",
				[format_currency(frm.doc.coupon_amount), format_currency(total_paid)]),
			indicator: "red"
		}, 10);
	}"""
new_update_monthly = """	let billed = frm.doc.grand_total || frm.doc.monthly_fee || 0;
	if ((frm.doc.coupon_amount || 0) > billed) {
		frappe.show_alert({
			message: __("Coupon of {0} is now more than the Grand Total of {1}. Reopen Add Coupon to change it.",
				[format_currency(frm.doc.coupon_amount), format_currency(billed)]),
			indicator: "red"
		}, 10);
	}"""
content = content.replace(old_update_monthly, new_update_monthly)


old_calculate_totals = """	let final_total = grand_total + outstanding;
	let balance = Math.max(0, final_total - (frm.doc.paid_amount || 0));
	frm.set_value('balance_amount', balance);"""
new_calculate_totals = """	let final_total = grand_total + outstanding;
	let balance = Math.max(0, final_total - (frm.doc.paid_amount || 0) - (frm.doc.coupon_amount || 0));
	frm.set_value('balance_amount', balance);"""
content = content.replace(old_calculate_totals, new_calculate_totals)

with open('fee_invoice.js', 'w') as f:
    f.write(content)
