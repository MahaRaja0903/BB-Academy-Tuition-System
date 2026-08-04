// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.query_reports["Birthday Report"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
			"default": ""
		},
		{
			"fieldname": "gender",
			"label": __("Gender"),
			"fieldtype": "Select",
			"options": "\nMale\nFemaleerro",
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
			"fieldname": "current_batch",
			"label": __("Batch"),
			"fieldtype": "Link",
			"options": "Batch",
			"default": ""
		}
	]
};
