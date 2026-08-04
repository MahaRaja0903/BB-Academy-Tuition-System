// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.query_reports["Pending Balance Report"] = {
	"filters": [
		{
			"fieldname": "student",
			"label": __("Student"),
			"fieldtype": "Link",
			"options": "Student",
			"default": ""
		},
		{
			"fieldname": "standard",
			"label": __("Standard"),
			"fieldtype": "Link",
			"options": "Standard",
			"default": ""
		},
		{
			"fieldname": "batch",
			"label": __("Batch"),
			"fieldtype": "Link",
			"options": "Batch",
			"default": ""
		},
		{
			"fieldname": "show_only_pending",
			"label": __("Show Only Pending Balances"),
			"fieldtype": "Check",
			"default": 1
		}
	]
};
