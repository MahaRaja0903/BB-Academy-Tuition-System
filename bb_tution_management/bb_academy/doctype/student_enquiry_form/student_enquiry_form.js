// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Enquiry Form", {
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
		frm.set_query("fee_preview_batch", function() {
			return { filters: { is_active: 1 } };
		});
		frm.set_query("street", function() {
			if (frm.doc.area) {
				return {
					filters: {
						area: frm.doc.area
					}
				};
			}
		});
	},
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status !== "Lost") {
			frm.add_custom_button(__("Create Admission Form"), () => {
				frappe.model.open_mapped_doc({
					method: "bb_tution_management.bb_academy.doctype.student_enquiry_form.student_enquiry_form.make_admission_form",
					frm: frm
				});
			}, __("Create"));
		}

		if (!frm.is_new() && frm.doc.status === "Converted") {
			frm.add_custom_button(__("Generate Admission URL"), () => {
				let base_url = frappe.urllib.get_base_url() + "/admission/new";
				let final_url = base_url + "?student_enquiry=" + encodeURIComponent(frm.doc.name);
				let message_text = `Hello ${frm.doc.applicant_name || ''}, please complete your admission form for BB Academy here: \n${final_url}`;
				let whatsapp_message = encodeURIComponent(message_text);

				let show_dialog = (phone, recipient_type, recipient_name) => {
					let digits = phone ? phone.replace(/[^0-9]/g, '') : '';
					let phone_param = digits ? `&phone=${digits}` : '';
					let whatsapp_link = `https://api.whatsapp.com/send?text=${whatsapp_message}${phone_param}`;

					let msg_dialog = frappe.msgprint({
						title: __('Admission URL Generated'),
						message: `
							<p>${__('Share this link with the student to fill their admission form:')}</p>
							<p><a href="${final_url}" target="_blank" style="word-break: break-all;">${final_url}</a></p>
							<div class="mt-3">
								<button class="btn btn-default btn-sm" onclick="frappe.utils.copy_to_clipboard('${final_url}')">
									${__('Copy to Clipboard')}
								</button>
								<a href="${whatsapp_link}" target="_blank" class="btn btn-success btn-sm ml-2 text-white wa-share-link" style="background-color: #25D366; border-color: #25D366;">
									<i class="fa fa-whatsapp"></i> ${__('Share via WhatsApp')}
								</a>
							</div>
						`,
						indicator: 'green'
					});

					// Keep a record of what went to whom -- see WhatsApp Message Log.
					msg_dialog.$wrapper.find('.wa-share-link').on('click', () => {
						frappe.call({
							method: "bb_tution_management.bb_academy.doctype.whatsapp_message_log.whatsapp_message_log.log_whatsapp_message",
							args: {
								reference_doctype: frm.doctype,
								reference_name: frm.doc.name,
								message: message_text,
								mobile_number: digits,
								message_type: "Admission Link",
								recipient_type: recipient_type,
								recipient_name: recipient_name
							}
						});
					});
				};

				let father_num = frm.doc.father_number;
				let mother_num = frm.doc.mother_number;

				if (father_num && mother_num) {
					let d = new frappe.ui.Dialog({
						title: 'Select Number for WhatsApp',
						fields: [
							{
								label: 'Mobile Number',
								fieldname: 'mobile_number',
								fieldtype: 'Select',
								options: `Father: ${father_num}\nMother: ${mother_num}`,
								reqd: 1
							}
						],
						primary_action_label: 'Generate Link',
						primary_action: (values) => {
							let is_father = values.mobile_number.includes('Father');
							d.hide();
							show_dialog(
								is_father ? father_num : mother_num,
								is_father ? "Father" : "Mother",
								is_father ? frm.doc.father_name : frm.doc.mother_name
							);
						}
					});
					d.show();
				} else if (father_num) {
					show_dialog(father_num, "Father", frm.doc.father_name);
				} else if (mother_num) {
					show_dialog(mother_num, "Mother", frm.doc.mother_name);
				} else {
					show_dialog(null);
				}
			}).removeClass('btn-default').addClass('btn-success text-white');
		}

		frm.trigger("toggle_group_field");
		refresh_fee_preview(frm);
	},
	fee_preview_batch(frm) {
		refresh_fee_preview(frm);
	},
	fee_preview_joining_date(frm) {
		refresh_fee_preview(frm);
	},
	fee_preview_yearly(frm) {
		refresh_fee_preview(frm);
	},
	academic_year(frm) {
		refresh_fee_preview(frm);
	},
	enquiry_date(frm) {
		if (frm.doc.enquiry_date && frm.doc.standard) {
			frm.trigger("set_academic_year");
		}
	},
	standard(frm) {
		frm.set_value("group", "");
		refresh_fee_preview(frm);
		if (frm.doc.standard) {
			frm.trigger("set_academic_year");
			frm.trigger("toggle_group_field");
		} else {
			frm.set_value("academic_year", "");
			frm.set_df_property("group", "hidden", 1);
		}
	},
	area(frm) {
		frm.set_value("street", "");
	},
	set_academic_year(frm) {
		if (!frm.doc.standard) return;
		let ref_date = frm.doc.enquiry_date || frappe.datetime.get_today();
		frappe.call({
			method: "bb_tution_management.bb_academy.doctype.student_enquiry_form.student_enquiry_form.get_academic_year",
			args: {
				date: ref_date,
				standard: frm.doc.standard
			},
			callback(r) {
				if (r.message) {
					frm.set_value("academic_year", r.message);
				} else {
					frm.set_value("academic_year", "");
				}
			}
		});
	},
	toggle_group_field(frm) {
		if (!frm.doc.standard) {
			frm.set_df_property("group", "hidden", 1);
			return;
		}
		// fetch if groups exist for this standard
		frappe.db.get_list("Standard Detail", {
			parent_doctype: "Group",
			filters: {
				parenttype: "Group",
				parentfield: "standard_detail",
				standard: frm.doc.standard
			},
			limit: 1
		}).then(records => {
			if (records && records.length > 0) {
				frm.set_df_property("group", "hidden", 0);
			} else {
				frm.set_df_property("group", "hidden", 1);
			}
		});
	}
});

// The fee quote for the parents. Worked out on the server by the Admission
// Form's own rules, so what is quoted here is what the admission will bill.
let fee_preview_timer = null;

function refresh_fee_preview(frm) {
	// Picking a standard also sets the academic year; ask the server once.
	clearTimeout(fee_preview_timer);
	fee_preview_timer = setTimeout(() => {
		frappe.call({
			method: "bb_tution_management.bb_academy.doctype.student_enquiry_form.student_enquiry_form.get_fee_preview",
			args: {
				standard: frm.doc.standard,
				batch: frm.doc.fee_preview_batch,
				academic_year: frm.doc.academic_year,
				joining_date: frm.doc.fee_preview_joining_date || frm.doc.enquiry_date,
				yearly: frm.doc.fee_preview_yearly
			},
			callback(r) {
				let p = r.message || {};
				let values = {
					fee_preview_starting_payment: p.starting_payment || 0,
					fee_preview_monthly_fee: p.monthly_fee || 0,
					fee_preview_first_payment: p.first_payment || 0,
					fee_preview_yearly_total: p.yearly_total || 0,
					fee_preview_yearly_savings: p.yearly_savings || 0
				};
				// Only touch the fields that moved, so opening a saved enquiry
				// does not mark it dirty.
				Object.keys(values).forEach(field => {
					if (flt(frm.doc[field]) !== flt(values[field])) frm.set_value(field, values[field]);
				});
				render_fee_breakdown(frm, p);
			}
		});
	}, 300);
}

function render_fee_breakdown(frm, p) {
	let wrapper = frm.get_field("fee_preview_breakdown").$wrapper;
	if (p.message || !(p.rows || []).length) {
		wrapper.html(p.message ? `<p class="text-muted">${frappe.utils.escape_html(p.message)}</p>` : "");
		return;
	}

	let fmt = value => format_currency(value);
	let body = p.rows.map(row => `
		<tr>
			<td>${__(row.month)}</td>
			<td class="text-right">${fmt(row.amount_need_to_pay)}</td>
			<td class="text-muted">${frappe.utils.escape_html(row.remarks || "")}</td>
		</tr>`).join("");

	let total_label = frm.doc.fee_preview_yearly ? __("Total Yearly Payment") : __("Amount to Pay at Joining");
	let total = frm.doc.fee_preview_yearly ? p.yearly_total : p.first_payment;
	let footer = `<tr><th>${total_label}</th><th class="text-right">${fmt(total)}</th><th></th></tr>`;
	if (frm.doc.fee_preview_yearly && p.yearly_savings) {
		footer += `<tr class="text-success"><th>${__("Saved by Paying Yearly")}</th><th class="text-right">${fmt(p.yearly_savings)}</th><th></th></tr>`;
	}
	if (!frm.doc.fee_preview_yearly) {
		footer += `<tr><td>${__("Then every month")}</td><td class="text-right">${fmt(p.monthly_fee)}</td><td></td></tr>`;
	}

	let notes = (p.notes || []).map(n => `<p class="text-muted small">${frappe.utils.escape_html(n)}</p>`).join("");

	wrapper.html(`
		<table class="table table-bordered table-sm">
			<thead><tr><th>${__("Month")}</th><th class="text-right">${__("Amount")}</th><th>${__("Remarks")}</th></tr></thead>
			<tbody>${body}</tbody>
			<tfoot>${footer}</tfoot>
		</table>
		${notes}
	`);
}
