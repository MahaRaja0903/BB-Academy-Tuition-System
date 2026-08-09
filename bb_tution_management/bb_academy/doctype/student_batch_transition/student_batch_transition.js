// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Batch Transition", {
	refresh(frm) {
		render_student_html(frm);
	},
	student(frm) {
		if (frm.doc.student) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Student",
					name: frm.doc.student
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('student_details_json', JSON.stringify(r.message));
						render_student_html(frm);
					}
				}
			});
		} else {
			frm.set_value('student_details_json', '');
			frm.get_field('student_html').$wrapper.html('');
		}
	},
	new_batch(frm) {
		if (frm.doc.previous_batch && frm.doc.new_batch) {
			if (frm.doc.previous_batch === frm.doc.new_batch) {
				frappe.msgprint(__("Previous Batch and New Batch cannot be the same."));
				frm.set_value('new_batch', '');
				return;
			}
			
			// determine promotion or demotion
			frappe.db.get_value('Batch', frm.doc.previous_batch, 'display_order', (prev) => {
				frappe.db.get_value('Batch', frm.doc.new_batch, 'display_order', (curr) => {
					if (prev && curr) {
						if (curr.display_order > prev.display_order) {
							frm.set_value('status', 'Promotion');
						} else if (curr.display_order < prev.display_order) {
							frm.set_value('status', 'Demote');
						} else {
							frm.set_value('status', 'Promotion');
						}
					}
				});
			});
		}
	}
});

function render_student_html(frm) {
	if (frm.doc.student_details_json) {
		try {
			let student = JSON.parse(frm.doc.student_details_json);
			let image_html = student.image ? `<img src="${student.image}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">` : `<div style="width: 100px; height: 100px; border-radius: 50%; background-color: #e2e8f0; display: flex; align-items: center; justify-content: center; color: #64748b; box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-weight: 500;">No Photo</div>`;
			
			let html = `
				<div style="display: flex; gap: 24px; align-items: center; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background: linear-gradient(145deg, #ffffff, #f8fafc); box-shadow: 0 2px 10px rgba(0,0,0,0.02);">
					<div style="flex-shrink: 0;">
						${image_html}
					</div>
					<div style="display: flex; flex-direction: column; gap: 8px;">
						<h3 style="margin: 0; color: #0f172a; font-size: 1.25rem; font-weight: 600;">${student.student_name}</h3>
						<div style="display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; font-size: 0.9rem; color: #475569;">
							<span style="font-weight: 500; color: #334155;">Admission No:</span>
							<span>${student.admission_number || '-'}</span>
							
							<span style="font-weight: 500; color: #334155;">Gender:</span>
							<span>${student.gender || '-'}</span>
							
							<span style="font-weight: 500; color: #334155;">Standard:</span>
							<span>${student.standard || '-'}</span>
							
							<span style="font-weight: 500; color: #334155;">Current Batch:</span>
							<span><span style="background-color: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 600;">${student.current_batch || '-'}</span></span>
						</div>
					</div>
				</div>
			`;
			frm.get_field('student_html').$wrapper.html(html);
		} catch (e) {
			console.error(e);
		}
	}
}
