// Copyright (c) 2026, Maha Raja and contributors
// For license information, please see license.txt

frappe.query_reports["Discontinued or Suspended Students"] = {
	"filters": [
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": "\nDiscontinued\nSuspended",
            "default": ""
        },
        {
            "fieldname": "month",
            "label": __("Month"),
            "fieldtype": "Select",
            "options": "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
            "default": ""
        },
        {
            "fieldname": "year",
            "label": __("Year"),
            "fieldtype": "Int",
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
        },
        {
            "fieldname": "gender",
            "label": __("Gender"),
            "fieldtype": "Select",
            "options": "\nBoys\nGirls",
            "default": ""
        }
	]
};
