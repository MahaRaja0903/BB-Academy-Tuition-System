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
        }
	]
};
