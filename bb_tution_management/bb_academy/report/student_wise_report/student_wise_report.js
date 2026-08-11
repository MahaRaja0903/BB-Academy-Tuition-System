// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.query_reports["Student Wise Report"] = {
	"filters": [
		{
			"fieldname": "standard",
			"label": __("Standard"),
			"fieldtype": "Link",
			"options": "Standard"
		},
		{
			"fieldname": "current_batch",
			"label": __("Batch"),
			"fieldtype": "Link",
			"options": "Batch"
		},
		{
			"fieldname": "academic_year",
			"label": __("Academic Year"),
			"fieldtype": "Link",
			"options": "Academic Year"
		},
		{
			"fieldname": "gender",
			"label": __("Gender"),
			"fieldtype": "Select",
			"options": "\nMale\nFemale\nOther"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nActive\nCompleted\nDiscontinued\nSuspended"
		}
	]
};
