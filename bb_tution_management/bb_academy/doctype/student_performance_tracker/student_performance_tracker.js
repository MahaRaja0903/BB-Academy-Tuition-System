// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Performance Tracker", {
	category(frm) {
		// The Select carries every category's options; clear a result that the
		// newly picked category does not offer so validate() cannot reject it.
		const allowed = {
			Study: ["Excellent", "Completed", "Incomplete"],
			Test: ["Full Mark", "Pass Mark", "Fail"],
			"Maths Test": ["Full Mark", "Pass Mark", "Fail"],
			Behaviour: ["Good", "Bad", "Worst"],
		}[frm.doc.category];

		if (allowed && !allowed.includes(frm.doc.result)) {
			frm.set_value("result", "");
		}
	},
});
