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

	function refresh_group(standard, is_initial = false, custom_url_params = null) {
		const academic_order = to_int(academic_order_by_standard[standard]);

		// the group field's depends_on reads this
		frappe.web_form.set_value("standard_academic_order", academic_order);

		let url_params = custom_url_params || new URLSearchParams(window.location.search);

		if (academic_order <= group_min_academic_order) {
			set_options("group", []);
			if (!is_initial) {
				frappe.web_form.set_value("group", "");
			}
			frappe.web_form.refresh_dependency();
			return;
		}

		frappe.call({
			method: OPTIONS_METHOD,
			args: { standard: standard },
			callback: function (r) {
				const data = (r && r.message) || {};
				set_options("group", data.groups);
				
				let url_group = url_params.get("group");
				if (is_initial && url_group && (data.groups || []).includes(url_group)) {
					frappe.web_form.set_value("group", url_group);
				} else if (!is_initial) {
					frappe.web_form.set_value("group", "");
				}
				frappe.web_form.refresh_dependency();
			},
		});
	}

	let is_setting_initial = false;

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

			let url_params = new URLSearchParams(window.location.search);
			
			if (url_params.has("student_enquiry")) {
				let enquiry_id = url_params.get("student_enquiry");
				frappe.call({
					method: "bb_tution_management.bb_academy.doctype.student_admission_form.student_admission_form.get_enquiry_details",
					args: { enquiry_name: enquiry_id },
					callback: function(res) {
						if (res.message && res.message.student_name) {
							is_setting_initial = true;
							let enq = res.message;
							url_params.set("group", enq.group || "");
							
							let promises = [];
							
							promises.push(frappe.web_form.set_value("student_name", enq.student_name));
							if (enq.gender) promises.push(frappe.web_form.set_value("gender", enq.gender));
							if (enq.date_of_birth) promises.push(frappe.web_form.set_value("date_of_birth", enq.date_of_birth));
							if (enq.school_name) promises.push(frappe.web_form.set_value("school_name", enq.school_name));
							if (enq.referred_by) promises.push(frappe.web_form.set_value("referred_by", enq.referred_by));
							
							if (enq.father_name) promises.push(frappe.web_form.set_value("father_name", enq.father_name));
							if (enq.mother_name) promises.push(frappe.web_form.set_value("mother_name", enq.mother_name));
							if (enq.father_mobile_number) promises.push(frappe.web_form.set_value("father_mobile_number", enq.father_mobile_number));
							if (enq.mother_mobile_number) promises.push(frappe.web_form.set_value("mother_mobile_number", enq.mother_mobile_number));
							
							if (enq.standard && academic_order_by_standard[enq.standard]) {
								promises.push(frappe.web_form.set_value("standard", enq.standard));
							}
							
							Promise.all(promises).then(() => {
								refresh_group(frappe.web_form.get_value("standard"), true, url_params);
								// Add a tiny delay to ensure all async events triggered by set_value have resolved
								setTimeout(() => is_setting_initial = false, 200);
							});
						} else {
							apply_url_params_fallback(url_params);
						}
					}
				});
			} else {
				apply_url_params_fallback(url_params);
			}
		},
	});

	function apply_url_params_fallback(url_params) {
		is_setting_initial = true;
		let promises = [];
		if (url_params.has("gender")) {
			promises.push(frappe.web_form.set_value("gender", url_params.get("gender")));
		}
		if (url_params.has("standard")) {
			let url_std = url_params.get("standard");
			if (academic_order_by_standard[url_std]) {
				promises.push(frappe.web_form.set_value("standard", url_std));
			}
		}
		Promise.all(promises).then(() => {
			refresh_group(frappe.web_form.get_value("standard"), true, url_params);
			setTimeout(() => is_setting_initial = false, 200);
		});
	}

	frappe.web_form.on("standard", function (field, value) {
		if (is_setting_initial) return;
		refresh_group(value, false, new URLSearchParams());
	});
});
