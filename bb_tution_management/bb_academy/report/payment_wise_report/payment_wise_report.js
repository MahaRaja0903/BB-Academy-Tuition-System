// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.query_reports["Payment Wise Report"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember"
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "standard",
			"label": __("Standard"),
			"fieldtype": "Link",
			"options": "Standard"
		},
		{
			"fieldname": "batch",
			"label": __("Batch"),
			"fieldtype": "Link",
			"options": "Batch"
		},
		{
			"fieldname": "gender",
			"label": __("Gender"),
			"fieldtype": "Select",
			"options": "\nMale\nFemale\nOther"
		}
	]
};
