// Public admission form (/admission).
//
// Standard and Group are Select fields here rather than Link fields: this form is
// open to Guests, and frappe.desk.search.search_link is not guest-whitelisted, so
// Link autocomplete returns nothing for a visitor who is not logged in. Both lists
// come from one guest-allowed endpoint instead.
//
// Group is only offered for senior standards (Standard.academic_order > 5) and is
// limited to the Groups that map to the chosen standard. Visibility is driven by
// the hidden standard_academic_order field, which the group field's depends_on reads.

frappe.ready(function () {
	const OPTIONS_METHOD =
		"bb_tution_management.bb_academy.doctype.student_admission_form.student_admission_form.get_admission_form_options";

	let academic_order_by_standard = {};
	let group_min_academic_order = 5;

	function to_int(value) {
		const parsed = parseInt(value, 10);
		return isNaN(parsed) ? 0 : parsed;
	}

	function set_options(fieldname, values) {
		const field = frappe.web_form.fields_dict[fieldname];
		if (!field) return;

		// leading blank so nothing is pre-selected
		const options = [""].concat(values || []);
		field.df.options = options.join("\n");
		field.refresh();
	}

	function refresh_group(standard) {
		const academic_order = to_int(academic_order_by_standard[standard]);

		// the group field's depends_on reads this
		frappe.web_form.set_value("standard_academic_order", academic_order);

		if (academic_order <= group_min_academic_order) {
			set_options("group", []);
			frappe.web_form.set_value("group", "");
			frappe.web_form.refresh_dependency();
			return;
		}

		frappe.call({
			method: OPTIONS_METHOD,
			args: { standard: standard },
			callback: function (r) {
				const data = (r && r.message) || {};
				set_options("group", data.groups);
				frappe.web_form.set_value("group", "");
				frappe.web_form.refresh_dependency();
			},
		});
	}

	// initial load: fill the Standard list
	frappe.call({
		method: OPTIONS_METHOD,
		callback: function (r) {
			const data = (r && r.message) || {};

			group_min_academic_order = to_int(data.group_min_academic_order) || 5;
			academic_order_by_standard = {};
			(data.standards || []).forEach(function (d) {
				academic_order_by_standard[d.value] = d.academic_order;
			});

			set_options(
				"standard",
				(data.standards || []).map(function (d) {
					return d.value;
				})
			);

			// hide Group until a standard is picked
			refresh_group(frappe.web_form.get_value("standard"));
		},
	});

	frappe.web_form.on("standard", function (field, value) {
		refresh_group(value);
	});
});
