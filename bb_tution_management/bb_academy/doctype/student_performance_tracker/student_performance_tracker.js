// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

const SUBJECT_QUERY =
	"bb_tution_management.bb_tution_management.doctype.subject.subject.subject_link_query";
const LESSON_QUERY =
	"bb_tution_management.bb_tution_management.doctype.lesson.lesson.lesson_link_query";

// Mirrors CATEGORY_RESULTS in bb_academy/performance_config.py.
const CATEGORY_RESULTS = {
	Study: ["Excellent", "Completed", "Incomplete", "Skipped"],
	Test: ["Full Mark", "Pass Mark", "Fail", "Skipped"],
	"Maths Test": ["Full Mark", "Pass Mark", "Fail", "Skipped"],
	"Accounts Test": ["Full Mark", "Pass Mark", "Fail", "Skipped"],
	Behaviour: ["Good", "Bad", "Worst"],
};

// A Table MultiSelect has no set_value; emptying the grid is how you clear it.
function clearLessons(frm) {
	if (!frm.doc.lessons?.length) return;
	frm.clear_table("lessons");
	frm.refresh_field("lessons");
}

frappe.ui.form.on("Student Performance Tracker", {
	setup(frm) {
		// Only subjects offered for the student's standard — a Subject with no
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
		// A lesson belongs to its subject; keeping it would mislabel the row.
		clearLessons(frm);
	},

	category(frm) {
		// The Select carries every category's options; clear a result that the
		// newly picked category does not offer so validate() cannot reject it.
		const allowed = CATEGORY_RESULTS[frm.doc.category];
		if (allowed && !allowed.includes(frm.doc.result)) {
			frm.set_value("result", "");
		}
	},

	// The checkbox and the grade are two views of the same fact — the server
	// reconciles them on save, and this keeps the form honest before that.
	skipped(frm) {
		if (frm.doc.skipped) frm.set_value("result", "Skipped");
		else if (frm.doc.result === "Skipped") frm.set_value("result", "");
	},

	result(frm) {
		frm.set_value("skipped", frm.doc.result === "Skipped" ? 1 : 0);
	},

	total_marks(frm) {
		// Half the paper passes, until someone types their own pass mark.
		if (!frm.doc.total_marks) return;
		if (frm.doc.pass_marks) return;
		frm.set_value("pass_marks", Math.round((frm.doc.total_marks / 2) * 2) / 2);
	},
});
