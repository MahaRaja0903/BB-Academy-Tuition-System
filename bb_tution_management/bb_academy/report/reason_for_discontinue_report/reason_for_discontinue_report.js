// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.query_reports["Reason For Discontinue Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			// The last 12 months, this one included.
			default: frappe.datetime.add_months(frappe.datetime.month_start(), -11),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "standard",
			label: __("Standard"),
			fieldtype: "Link",
			options: "Standard",
		},
		{
			fieldname: "current_batch",
			label: __("Batch"),
			fieldtype: "Link",
			options: "Batch",
		},
		{
			fieldname: "discontinue_reason_category",
			label: __("Reason Category"),
			fieldtype: "Link",
			options: "Discontinue Reason",
		},
		{
			fieldname: "include_rejoined",
			label: __("Include Rejoined Students"),
			fieldtype: "Check",
			default: 1,
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.indent === 0 && ["label", "count"].includes(column.fieldname)) {
			return `<b>${value}</b>`;
		}
		if (data && column.fieldname === "current_status" && data.current_status) {
			const color = data.rejoined_date ? "green" : "red";
			return `<span class="indicator-pill ${color}">${value}</span>`;
		}
		return value;
	},
};
