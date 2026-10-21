// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.query_reports["Discount Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_start()
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "student",
			"label": __("Student"),
			"fieldtype": "Link",
			"options": "Student"
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
			"fieldname": "discount_reason",
			"label": __("Discount Reason"),
			"fieldtype": "Select",
			"options": "\nSiblings\nMonth Last Few Days\nLong Absent\nOthers ( Reason Box )"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nUnpaid\nPartially Paid\nPaid"
		}
	]
};
