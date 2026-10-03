// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

const REFUND_APPROVER_ROLES = ["System Manager", "Administrator"];

frappe.ui.form.on("Fee Refund", {
	refresh(frm) {
		const is_approver = REFUND_APPROVER_ROLES.some((role) => frappe.user.has_role(role));
		frm.set_df_property("approval_status", "read_only", !is_approver || frm.doc.docstatus !== 0);
		frm.set_df_property("management_remarks", "read_only", !is_approver || frm.doc.docstatus !== 0);

		if (frm.doc.docstatus === 0 && frm.doc.approval_status === "Rejected") {
			frm.dashboard.set_headline_alert(__("Management rejected this refund."), "red");
		} else if (frm.doc.docstatus === 0 && frm.doc.approval_status === "Requested") {
			frm.dashboard.set_headline_alert(__("Waiting for management approval."), "orange");
		}
	},

	student(frm) {
		frm.trigger("fetch_paid_amount");
	},

	refund_for(frm) {
		frm.trigger("fetch_paid_amount");
	},

	fetch_paid_amount(frm) {
		if (!frm.doc.student || !frm.doc.refund_for) {
			frm.set_value("paid_amount", 0);
			return;
		}
		frappe.call({
			method: "bb_tution_management.bb_academy.doctype.fee_refund.fee_refund.get_paid_amount",
			args: { student: frm.doc.student, refund_for: frm.doc.refund_for },
			callback(r) {
				frm.set_value("paid_amount", flt(r.message));
				if (!flt(r.message)) {
					frappe.show_alert({
						message: __("No payment found for {0}.", [frm.doc.refund_for]),
						indicator: "orange",
					});
				}
			},
		});
	},
});
