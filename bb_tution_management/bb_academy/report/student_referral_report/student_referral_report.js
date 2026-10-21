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
            "fieldname": "coupon_status",
            "label": __("Coupon Status"),
            "fieldtype": "Select",
            "options": "\nHas Available Coupons\nHas Used Coupons\nHas Expired Coupons\nNo Coupons",
            "default": ""
        }
	]
};
