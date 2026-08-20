
frappe.query_reports["Late Entry Report"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.month_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.month_end(), "reqd": 1},
        {"fieldname":"min_late", "label":"Minimum Late Entries", "fieldtype":"Int", "default": 1}
    ]
};
