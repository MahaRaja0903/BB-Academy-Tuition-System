// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.query_reports["Payment Report"] = {
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
			"fieldname": "standard",
			"label": __("Standard"),
			"fieldtype": "MultiSelectList",
			"get_data": function (txt) {
				return frappe.db.get_link_options("Standard", txt);
			}
		},
		{
			"fieldname": "batch",
			"label": __("Batch"),
			"fieldtype": "MultiSelectList",
			"get_data": function (txt) {
				return frappe.db.get_link_options("Batch", txt);
			}
		},
		{
			"fieldname": "gender",
			"label": __("Gender"),
			"fieldtype": "Select",
			"options": "\nBoys\nGirls"
		},
		{
			"fieldname": "payment_method",
			"label": __("Payment Method"),
			"fieldtype": "Select",
			"options": "\nCash\nGPAY\nScanner"
		},
		{
			"fieldname": "fee_type",
			"label": __("Payment Type"),
			"fieldtype": "Select",
			"options": "\nStarting Payment\nMonthly"
		}
	],

	// The totals at the foot of the table are not payments, so they are set
	// apart from the rows above them.
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (data && data.is_summary) {
			value = `<span style="font-weight: 600">${value}</span>`;
		} else if (data) {
			if (column.fieldname === "payment_method" && data.payment_method === "Split Up") {
				value = `<span style="color: var(--orange-500, orange); font-weight: 600;">${value}</span>`;
			}
			// One invoice can cover the starting payment and a month or two at
			// once, so the label reads "Starting Payment, September" and the
			// starting part is picked out of it rather than matched whole.
			if (column.fieldname === "payment_type" && data.has_starting_payment) {
				value = value.replace(
					/Starting Payment/g,
					`<span style="color: var(--blue-500, blue); font-weight: 600;">$&</span>`
				);
			}
			// The staff can edit a student's Starting Payment or Monthly Fee
			// with a reason; showing it here answers "why is this amount low?"
			// without opening the Student. The name is coloured with it so the
			// students on an edited fee can be picked out at a glance -- a colour
			// of its own, not the orange of a Split Up or the blue of a starting
			// payment, both of which can land on the same row.
			if (column.fieldname === "student_name" && data.fee_reason) {
				const reason = frappe.utils.escape_html(data.fee_reason);
				value = `<div title="${reason}" style="color: var(--purple-500, #9c45e3); font-weight: 600; line-height: 1.2;">${value}</div>
					<div title="${reason}" style="color: var(--purple-500, #9c45e3); font-size: 10px; line-height: 1.2; margin-top: 2px; overflow: hidden; text-overflow: ellipsis;">${reason}</div>`;
			}
		}

		return value;
	},

	// The student name can carry a second line with the reason its fee was
	// edited, which the default row height clips.
	get_datatable_options: function (options) {
		return Object.assign(options, { cellHeight: 46 });
	},

	// Every standard starts out selected. onload runs before the first refresh
	// with the report's _no_refresh flag still set, so setting the value on the
	// control directly seeds the filter without running the report twice.
	onload: function (report) {
		let filter = report.get_filter("standard");
		if (!filter || (filter.get_value() || []).length) {
			return;
		}

		return frappe.db.get_list("Standard", {
			fields: ["name"],
			order_by: "academic_order asc",
			limit: 0
		}).then(rows => {
			filter.set_value(rows.map(row => row.name));
		});
	}
};
