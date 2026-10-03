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
	},
	enquiry_date(frm) {
		if (frm.doc.enquiry_date && frm.doc.standard) {
			frm.trigger("set_academic_year");
		}
	},
	standard(frm) {
		frm.set_value("group", "");
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
