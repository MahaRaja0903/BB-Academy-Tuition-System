// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

const SUBJECT_QUERY =
	"bb_tution_management.bb_tution_management.doctype.subject.subject.subject_link_query";
const LESSON_QUERY =
	"bb_tution_management.bb_tution_management.doctype.lesson.lesson.lesson_link_query";

// A Table MultiSelect has no set_value; emptying the grid is how you clear it.
function clearLessons(frm) {
	if (!frm.doc.lessons?.length) return;
	frm.clear_table("lessons");
	frm.refresh_field("lessons");
}

frappe.ui.form.on("Student Performance Session", {
	setup(frm) {
		// Only subjects offered for the standard on this form — a Subject with no
		// Standard Applicable rows is offered to every standard.
		frm.set_query("subject", () => ({
			query: SUBJECT_QUERY,
			filters: { standard: frm.doc.standard },
		}));

		// Lessons are mapped to one subject of one standard, so both narrow the
		// list. A Table MultiSelect has no grid, so the query goes on the field
		// itself — the three-argument set_query is for child tables only and
		// throws here, which takes the whole form render down with it. The
		// control drops what is already picked from its own dropdown, so the
		// same lesson cannot be added twice.
		frm.set_query("lessons", () => ({
			query: LESSON_QUERY,
			filters: { standard: frm.doc.standard, subject: frm.doc.subject },
		}));
	},

	standard(frm) {
		// The old pick may not be offered for the new standard.
		if (frm.doc.subject) frm.set_value("subject", "");
		clearLessons(frm);
	},

	subject(frm) {
		// A lesson belongs to its subject; keeping it would mislabel the session.
		clearLessons(frm);
	},

	total_marks(frm) {
		// Half the paper passes. Set it whenever the total changes and nobody has
		// typed their own pass mark yet.
		if (!frm.doc.total_marks) return;
		if (frm.doc.pass_marks) return;
		frm.set_value("pass_marks", Math.round((frm.doc.total_marks / 2) * 2) / 2);
	},
});
