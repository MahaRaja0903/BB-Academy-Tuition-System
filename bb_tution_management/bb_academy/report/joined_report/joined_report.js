// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.query_reports["Joined Report"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
			"default": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][new Date().getMonth()]
		},
		{
			"fieldname": "year",
			"label": __("Year"),
			"fieldtype": "Int",
			"default": new Date().getFullYear()
		},
		{
			"fieldname": "gender",
			"label": __("Gender"),
			"fieldtype": "Select",
			"options": "\nBoys\nGirls",
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
