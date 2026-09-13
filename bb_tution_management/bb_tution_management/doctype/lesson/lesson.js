// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lesson', {
	setup(frm) {
		// A lesson maps to one subject of one standard, so the Subject picker
		// has to obey the same "offered for this standard" rule the rest of the
		// module does.
		frm.set_query('subject', () => ({
			query: 'bb_tution_management.bb_tution_management.doctype.subject.subject.subject_link_query',
			filters: { standard: frm.doc.standard },
		}))
	},

	standard(frm) {
		if (frm.doc.subject) frm.set_value('subject', null)
	},
})
