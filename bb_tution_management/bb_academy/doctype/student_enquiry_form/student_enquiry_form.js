// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Enquiry Form", {
	setup(frm) {
		frm.set_query("standard", function() {
			return {
				order_by: "academic_order asc"
			};
		});
	},
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status !== "Converted") {
			frm.add_custom_button(__("Create Admission Form"), () => {
				frappe.call({
					method: "bb_tution_management.bb_academy.doctype.student_enquiry_form.student_enquiry_form.make_admission_form",
					args: {
						source_name: frm.doc.name
					},
					callback(r) {
						if (r.message) {
							const doc = frappe.model.sync(r.message)[0];
							frappe.set_route("Form", doc.doctype, doc.name);
						}
					}
				});
			}, __("Create"));
		}
	}
});
