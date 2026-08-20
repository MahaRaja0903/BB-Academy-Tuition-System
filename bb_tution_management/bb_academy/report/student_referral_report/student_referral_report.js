// Copyright (c) 2026, Maha Raja and contributors
// For license information, please see license.txt

frappe.query_reports["Student Referral Report"] = {
	"filters": [
        {
            "fieldname": "referrer",
            "label": __("Referrer Student"),
            "fieldtype": "Link",
            "options": "Student",
            "default": ""
        }
	]
};
