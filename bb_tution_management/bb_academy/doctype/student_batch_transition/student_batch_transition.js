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
						let student_info = r.message;
						frappe.call({
							method: "frappe.client.get_list",
							args: {
								doctype: "Student Batch Transition",
								filters: {
									student: frm.doc.student,
									docstatus: 1
								},
								fields: ["name", "previous_batch", "new_batch", "effective_date", "status"],
								order_by: "effective_date desc"
							},
							callback: function(history_r) {
								student_info.transition_history = history_r.message || [];
								frm.set_value('student_details_json', JSON.stringify(student_info));
								render_student_html(frm);
							}
						});
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
			
			// Determine promotion or demotion. display_order ranks batches
			// best-first, so moving to a higher display_order (1 -> 2) is a
			// demotion. The server re-derives this on validate -- this is only
			// so the form shows it straight away.
			frappe.db.get_value('Batch', frm.doc.previous_batch, 'display_order', (prev) => {
				frappe.db.get_value('Batch', frm.doc.new_batch, 'display_order', (curr) => {
					if (prev && curr) {
						frm.set_value(
							'status',
							cint(curr.display_order) > cint(prev.display_order) ? 'Demote' : 'Promotion'
						);
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
			
			let history_html = '';
			if (student.transition_history && student.transition_history.length > 0) {
				history_html += `
					<div style="margin-top: 24px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
						<h4 style="margin: 0 0 16px 0; color: #1e293b; font-size: 1.1rem; font-weight: 600;">Past Batch Transitions</h4>
						<div style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #ffffff;">
							<table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
								<thead>
									<tr style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
										<th style="padding: 12px 16px; font-weight: 600; color: #475569;">Date</th>
										<th style="padding: 12px 16px; font-weight: 600; color: #475569;">From Batch</th>
										<th style="padding: 12px 16px; font-weight: 600; color: #475569;">To Batch</th>
										<th style="padding: 12px 16px; font-weight: 600; color: #475569;">Status</th>
									</tr>
								</thead>
								<tbody>
				`;
				student.transition_history.forEach((t, index) => {
					let date_str = frappe.datetime.str_to_user(t.effective_date);
					let status_color = t.status === 'Promotion' ? '#10b981' : (t.status === 'Demote' ? '#ef4444' : '#64748b');
					let status_bg = t.status === 'Promotion' ? '#d1fae5' : (t.status === 'Demote' ? '#fee2e2' : '#f1f5f9');
					let border_bottom = index < student.transition_history.length - 1 ? 'border-bottom: 1px solid #f1f5f9;' : '';
					
					history_html += `
									<tr style="${border_bottom} transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#f8fafc'" onmouseout="this.style.backgroundColor='transparent'">
										<td style="padding: 12px 16px; color: #334155;">${date_str}</td>
										<td style="padding: 12px 16px; color: #334155;">${t.previous_batch || '-'}</td>
										<td style="padding: 12px 16px; color: #334155; font-weight: 500;">${t.new_batch || '-'}</td>
										<td style="padding: 12px 16px;">
											<span style="background-color: ${status_bg}; color: ${status_color}; padding: 4px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.025em;">${t.status || '-'}</span>
										</td>
									</tr>
					`;
				});
				history_html += `
								</tbody>
							</table>
						</div>
					</div>
				`;
			} else {
				history_html += `
					<div style="margin-top: 24px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
						<h4 style="margin: 0 0 16px 0; color: #1e293b; font-size: 1.1rem; font-weight: 600;">Past Batch Transitions</h4>
						<div style="padding: 24px; background-color: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; text-align: center; color: #64748b; font-size: 0.95rem;">
							<div style="margin-bottom: 8px;">
								<svg style="width: 32px; height: 32px; color: #94a3b8; margin: 0 auto;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
								</svg>
							</div>
							No previous batch transitions found for this student.
						</div>
					</div>
				`;
			}

			let html = `
				<div style="display: flex; flex-direction: column; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background: linear-gradient(145deg, #ffffff, #f8fafc); box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
					<div style="display: flex; gap: 24px; align-items: center;">
						<div style="flex-shrink: 0;">
							${image_html}
						</div>
						<div style="display: flex; flex-direction: column; gap: 10px; flex-grow: 1;">
							<h3 style="margin: 0; color: #0f172a; font-size: 1.4rem; font-weight: 700;">${student.student_name}</h3>
							<div style="display: grid; grid-template-columns: auto 1fr; gap: 6px 16px; font-size: 0.95rem; color: #475569;">
								<span style="font-weight: 500; color: #64748b;">Admission No:</span>
								<span style="color: #1e293b; font-weight: 500;">${student.admission_number || '-'}</span>
								
								<span style="font-weight: 500; color: #64748b;">Gender:</span>
								<span style="color: #1e293b;">${student.gender || '-'}</span>
								
								<span style="font-weight: 500; color: #64748b;">Standard:</span>
								<span style="color: #1e293b;">${student.standard || '-'}</span>
								
								<span style="font-weight: 500; color: #64748b;">Current Batch:</span>
								<span><span style="background-color: #e0f2fe; color: #0284c7; padding: 4px 12px; border-radius: 999px; font-size: 0.8rem; font-weight: 600; letter-spacing: 0.025em; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">${student.current_batch || '-'}</span></span>
							</div>
						</div>
					</div>
					${history_html}
				</div>
			`;
			frm.get_field('student_html').$wrapper.html(html);
		} catch (e) {
			console.error(e);
		}
	}
}
