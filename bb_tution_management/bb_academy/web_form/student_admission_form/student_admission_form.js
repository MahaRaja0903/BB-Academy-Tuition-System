frappe.ready(function() {
	frappe.web_form.on('standard', function(field, value) {
		frappe.web_form.set_value('group', '');
	});
	
	frappe.web_form.fields_dict['group'].get_query = function() {
		return {
			query: 'bb_tution_management.bb_tution_management.doctype.group.group.get_groups_by_standard',
			filters: {
				'standard': frappe.web_form.get_value('standard')
			}
		};
	};
});