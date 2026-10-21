// Copyright (c) 2026, Maha Raja  and contributors
// For license information, please see license.txt

frappe.query_reports["Student Incomplete Data Report"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nActive\nCompleted\nDiscontinued\nSuspended",
			default: "Active",
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
			fieldname: "school_name",
			label: __("School"),
			fieldtype: "Link",
			options: "School",
		},
		{
			fieldname: "missing_field",
			label: __("Missing Field"),
			fieldtype: "Select",
			options: [
				{ value: "", label: "" },
				{ value: "image", label: __("Photo") },
				{ value: "date_of_birth", label: __("Date of Birth") },
				{ value: "blood_group", label: __("Blood Group") },
				{ value: "school_name", label: __("School") },
				{ value: "father_name", label: __("Father Name") },
				{ value: "father_mobile_number", label: __("Father Mobile") },
				{ value: "father_occupation", label: __("Father Occupation") },
				{ value: "mother_name", label: __("Mother Name") },
				{ value: "mother_mobile_number", label: __("Mother Mobile") },
				{ value: "mother_occupation", label: __("Mother Occupation") },
				{ value: "preferred_whatsapp_number", label: __("WhatsApp Number") },
				{ value: "address", label: __("Address") },
				{ value: "area", label: __("Area") },
				{ value: "street_name", label: __("Street Name") },
			],
		},
		{
			fieldname: "photo_missing_only",
			label: __("Photo Missing Only"),
			fieldtype: "Check",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;

		if (column.fieldname === "photo") {
			const color = data.photo === "Missing" ? "red" : "green";
			return `<span class="indicator-pill ${color}">${value}</span>`;
		}
		if (column.fieldname === "missing_details") {
			return `<span class="text-danger">${value}</span>`;
		}
		return value;
	},
};
