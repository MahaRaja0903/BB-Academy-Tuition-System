// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

const SUBJECT_QUERY =
	"bb_tution_management.bb_tution_management.doctype.subject.subject.subject_link_query";

frappe.ui.form.on("Student Performance Session", {
	setup(frm) {
		// Only subjects offered for the standard on this form — a Subject with no
		// Standard Applicable rows is offered to every standard.
		frm.set_query("subject", () => ({
			query: SUBJECT_QUERY,
			filters: { standard: frm.doc.standard },
		}));
	},

	standard(frm) {
		// The old pick may not be offered for the new standard.
		if (frm.doc.subject) frm.set_value("subject", "");
	},
});
