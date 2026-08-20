// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Enquiry Form", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.academic_year) {
			frm.trigger("set_academic_year");
		}
	},
	setup(frm) {
		frm.set_query("standard", function() {
			return {
				query: "bb_tution_management.bb_academy.doctype.student_admission_form.student_admission_form.get_standard_ordered"
			};
		});
	},
	refresh(frm) {
		if (frm.is_new() && !frm.doc.academic_year) {
			frm.trigger("set_academic_year");
		}
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
	},
	enquiry_date(frm) {
		if (frm.doc.enquiry_date) {
			frm.trigger("set_academic_year");
		}
	},
	standard(frm) {
		if (frm.doc.standard) {
			frm.trigger("set_academic_year");
		}
	},
	set_academic_year(frm) {
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
				}
			}
		});
	}
});
