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
            "fieldtype": "MultiSelectList",
            "get_data": function (txt) {
                return frappe.db.get_link_options("Standard", txt);
            }
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
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		const flag = {
			starting_payment_status: data.starting_payment_status,
			last_month_fee_status: data.last_month_fee_status,
		}[column.fieldname];
		if (column.fieldname === "total_to_pay" && data.total_to_pay > 0) {
			return `<span style="color: var(--red-600); font-weight: 600;">${value}</span>`;
		}
		if (flag === "Not Paid" || flag === "Partial") {
			value = `<span style="color: var(--red-600); font-weight: 600;">${value}</span>`;
		} else if (flag && flag.startsWith("Paid")) {
			value = `<span style="color: var(--green-600);">${value}</span>`;
		}
		return value;
	}
};
