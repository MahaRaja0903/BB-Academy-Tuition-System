// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.query_reports["Pending Performance Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: "From Date",
			fieldtype: "Date",
			// Performance tracking started on 1 October 2026.
			default: "2026-10-01",
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: "To Date",
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "view",
			label: "View",
			fieldtype: "Select",
			options: "Student Wise\nDate Wise",
			default: "Student Wise",
		},
		{ fieldname: "standard", label: "Standard", fieldtype: "Link", options: "Standard" },
		{ fieldname: "batch", label: "Batch", fieldtype: "Link", options: "Batch" },
		{
			fieldname: "gender",
			label: "Gender",
			fieldtype: "Select",
			options: "\nBoys\nGirls",
		},
		{
			fieldname: "category",
			label: "Category",
			fieldtype: "Select",
			options: "\nStudy\nTest\nH.W\nBehaviour",
			// Blank checks all four categories.
		},
		{ fieldname: "student", label: "Student", fieldtype: "Link", options: "Student" },
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname.endsWith("_pending") && data && data[column.fieldname]) {
			value = `<span style="color: var(--red-600); font-weight: 600;">${value}</span>`;
		}
		return value;
	},
};
