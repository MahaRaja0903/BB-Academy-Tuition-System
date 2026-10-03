// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.listview_settings["Student"] = {
	onload(listview) {
		if (!frappe.user.has_role(["System Manager", "Administrator", "Receptionist"])) return;

		listview.page.add_inner_button(__("Send Missing Details Message"), () => {
			show_missing_details_dialog();
		}, __("WhatsApp"));
	},
};

// Every active student's parent gets their own /student_details link through
// the missing_details_message-en template.
function show_missing_details_dialog() {
	const method = "bb_tution_management.bb_academy.missing_details.";

	let dialog = new frappe.ui.Dialog({
		title: __("Send Missing Details Message"),
		fields: [
			{
				fieldtype: "Date",
				fieldname: "submit_by",
				label: __("Submit By"),
				reqd: 1,
				default: frappe.datetime.add_days(frappe.datetime.get_today(), 7),
				description: __("Shown in the message as the last date to update the details."),
			},
			{
				fieldtype: "Check",
				fieldname: "only_missing",
				label: __("Only students whose details are still missing"),
				default: 1,
				description: __("Father or mother occupation is blank."),
			},
			{
				fieldtype: "Check",
				fieldname: "skip_already_sent",
				label: __("Skip students already sent this message"),
				default: 1,
			},
			{ fieldtype: "HTML", fieldname: "summary" },
		],
		primary_action_label: __("Send"),
		primary_action(values) {
			frappe.confirm(
				__("Send the WhatsApp message to {0} student(s)?", [dialog.to_send || 0]),
				() => {
					frappe.call({
						method: method + "send_missing_details_message",
						args: values,
						freeze: true,
						callback(r) {
							dialog.hide();
							frappe.show_alert({ message: r.message, indicator: "green" }, 8);
						},
					});
				}
			);
		},
	});

	let refresh_summary = () => {
		let values = dialog.get_values(true);
		frappe.call({
			method: method + "get_missing_details_summary",
			args: {
				only_missing: values.only_missing,
				skip_already_sent: values.skip_already_sent,
			},
			callback(r) {
				let s = r.message;
				dialog.to_send = s.to_send;
				dialog.get_primary_btn().prop("disabled", !s.to_send);

				let html = `<div style="padding:10px 12px;border-radius:6px;background:#eff6ff;color:#1e3a8a;font-size:13px;">
					${__("Will be sent to <b>{0}</b> active student(s).", [s.to_send])}
				</div>`;
				if (s.no_number.length) {
					html += `<div style="margin-top:8px;padding:10px 12px;border-radius:6px;background:#fef3c7;color:#92400e;font-size:13px;">
						${__("No WhatsApp number, will be skipped:")}
						${s.no_number.map(x => `${frappe.utils.escape_html(x.student_name || "")} (${x.name})`).join(", ")}
					</div>`;
				}
				dialog.fields_dict.summary.$wrapper.html(html);
			},
		});
	};

	dialog.fields_dict.only_missing.$input.on("change", refresh_summary);
	dialog.fields_dict.skip_already_sent.$input.on("change", refresh_summary);
	dialog.show();
	refresh_summary();
}
