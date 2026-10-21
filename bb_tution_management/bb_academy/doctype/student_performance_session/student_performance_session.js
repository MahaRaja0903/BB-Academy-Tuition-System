// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

const SUBJECT_QUERY =
	"bb_tution_management.bb_tution_management.doctype.subject.subject.subject_link_query";
const LESSON_QUERY =
	"bb_tution_management.bb_tution_management.doctype.lesson.lesson.lesson_link_query";

// A Table MultiSelect has no set_value; emptying the grid is how you clear it.
function clearTable(frm, fieldname) {
	if (!frm.doc[fieldname]?.length) return;
	frm.clear_table(fieldname);
	frm.refresh_field(fieldname);
}

function pickedSubjects(frm) {
	return (frm.doc.subjects || []).map((row) => row.subject).filter(Boolean);
}

frappe.ui.form.on("Student Performance Session", {
	setup(frm) {
		// Only subjects offered for the standard on this form — a Subject with no
		// Standard Applicable rows is offered to every standard.
		frm.set_query("subjects", () => ({
			query: SUBJECT_QUERY,
			filters: { standard: frm.doc.standard },
		}));

		// Lessons are mapped to one subject of one standard, so the standard and
		// the picked subjects narrow the list. A Table MultiSelect has no grid, so
		// the query goes on the field itself — the three-argument set_query is for
		// child tables only and throws here, which takes the whole form render
		// down with it. The
		// control drops what is already picked from its own dropdown, so the
		// same lesson cannot be added twice.
		frm.set_query("lessons", () => ({
			query: LESSON_QUERY,
			filters: { standard: frm.doc.standard, subject: pickedSubjects(frm) },
		}));
	},

	standard(frm) {
		// The old picks may not be offered for the new standard.
		clearTable(frm, "subjects");
		clearTable(frm, "lessons");
	},

	total_marks(frm) {
		// Half the paper passes. Set it whenever the total changes and nobody has
		// typed their own pass mark yet.
		if (!frm.doc.total_marks) return;
		if (frm.doc.pass_marks) return;
		frm.set_value("pass_marks", Math.round((frm.doc.total_marks / 2) * 2) / 2);
	},
});
