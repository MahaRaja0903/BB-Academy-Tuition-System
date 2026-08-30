// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.query_reports["Pending Balance Break Down"] = {
	"filters": [
		{
			"fieldname": "standard",
			"label": __("Standard"),
			"fieldtype": "MultiSelectList",
			"get_data": function (txt) {
				return frappe.db.get_link_options("Standard", txt);
			}
		},
		{
			"fieldname": "batch",
			"label": __("Batch"),
			"fieldtype": "MultiSelectList",
			"get_data": function (txt) {
				return frappe.db.get_link_options("Batch", txt);
			}
		},
		{
			"fieldname": "gender",
			"label": __("Gender"),
			"fieldtype": "Select",
			"options": "\nBoys\nGirls"
		},
		{
			"fieldname": "fee_type",
			"label": __("Fee Type"),
			"fieldtype": "Select",
			"options": "\nStarting Payment\nMonthly"
		}
	],

	// Every standard starts out selected. onload runs before the first refresh
	// with the report's _no_refresh flag still set, so setting the value on the
	// control directly seeds the filter without running the report twice.
	onload: function (report) {
		let filter = report.get_filter("standard");
		if (!filter || (filter.get_value() || []).length) {
			return;
		}

		return frappe.db.get_list("Standard", {
			fields: ["name"],
			order_by: "academic_order asc",
			limit: 0
		}).then(rows => {
			filter.set_value(rows.map(row => row.name));
		});
	}
};
