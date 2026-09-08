// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Performance Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: "From Date",
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: "To Date",
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
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
			options: "\nStudy\nTest\nMaths Test\nBehaviour",
			// Blank shows every category side by side.
		},
		{ fieldname: "student", label: "Student", fieldtype: "Link", options: "Student" },
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// The columns that mean "something went wrong" read red so a month's
		// problem students stand out without sorting.
		if (["study_incomplete", "test_fail", "maths_fail", "behaviour_worst"].includes(column.fieldname)) {
			if (data && data[column.fieldname]) {
				value = `<span style="color: var(--red-600); font-weight: 600;">${value}</span>`;
			}
		}
		if (column.fieldname === "behaviour_bad" && data && data.behaviour_bad) {
			value = `<span style="color: var(--orange-600, #d97706); font-weight: 600;">${value}</span>`;
		}
		return value;
	},
};
