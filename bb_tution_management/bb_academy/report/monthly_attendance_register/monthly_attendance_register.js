
frappe.query_reports["Monthly Attendance Register"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.month_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.month_end(), "reqd": 1},
        {"fieldname":"standard", "label":"Standard", "fieldtype":"Link", "options":"Standard"},
        {"fieldname":"batch", "label":"Batch", "fieldtype":"Link", "options":"Batch"}
    ]
};
