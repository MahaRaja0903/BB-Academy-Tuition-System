// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.query_reports["Pending Call Works Report"] = {
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
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "call_work",
			label: "Call Work",
			fieldtype: "Select",
			options: "\nPending Call Works\nAttendance Call Works",
		},
		{
			fieldname: "status",
			label: "Status",
			fieldtype: "Select",
			// Pending and Missed are today's list: they show only when To Date
			// reaches today.
			options: "\nCalled\nCalled Late\nPending\nMissed",
		},
		{
			fieldname: "called_by",
			label: "In-charge (Called By)",
			fieldtype: "Link",
			options: "Staff",
		},
		{
			fieldname: "category",
			label: "Category",
			fieldtype: "Select",
			options: "\nH.W\nTest\nStudy\nClass\nBehaviour\nAttendance",
		},
		{
			fieldname: "priority",
			label: "Priority",
			fieldtype: "Select",
			options: "\nNormal\nImportant\nHigh Priority",
		},
		{ fieldname: "standard", label: "Standard", fieldtype: "Link", options: "Standard" },
		{ fieldname: "batch", label: "Batch", fieldtype: "Link", options: "Batch" },
		{
			fieldname: "gender",
			label: "Gender",
			fieldtype: "Select",
			options: "\nBoys\nGirls",
		},
		{ fieldname: "student", label: "Student", fieldtype: "Link", options: "Student" },
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;

		if (column.fieldname === "status") {
			const color = {
				Called: "green",
				"Called Late": "orange",
				Pending: "blue",
				Missed: "red",
			}[data.status];
			if (color) value = `<span class="indicator-pill ${color}">${value}</span>`;
		}
		if (column.fieldname === "missed" && data.missed) {
			value = `<span style="color: var(--red-600); font-weight: 600;">${value}</span>`;
		}
		if (column.fieldname === "priority" && data.priority === "High Priority") {
			value = `<span style="color: var(--red-600); font-weight: 600;">${value}</span>`;
		}
		return value;
	},
};
