// Copyright (c) 2026, Maha Raja and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bulk Fee Invoice Tool", {
	generate_invoices(frm) {
		if (!frm.doc.academic_year || !frm.doc.fee_month) {
			frappe.msgprint(__("Please select Academic Year and Fee Month."));
			return;
		}

		frappe.confirm(
			__("Are you sure you want to generate Bulk Invoices for {0}?", [frm.doc.fee_month]),
			function() {
				frappe.call({
					method: "bb_tution_management.bb_academy.doctype.bulk_fee_invoice_tool.bulk_fee_invoice_tool.generate_invoices",
					args: {
						academic_year: frm.doc.academic_year,
						fee_month: frm.doc.fee_month
					},
					freeze: true,
					freeze_message: __("Generating Invoices..."),
					callback: function(r) {
						if (!r.exc && r.message !== undefined) {
							frappe.msgprint(__("Successfully generated {0} Fee Invoices.", [r.message]));
						}
					}
				});
			}
		);
	}
});
