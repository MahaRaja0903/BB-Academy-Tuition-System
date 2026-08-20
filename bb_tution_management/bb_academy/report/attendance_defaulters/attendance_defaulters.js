
frappe.query_reports["Attendance Defaulters"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.month_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.month_end(), "reqd": 1},
        {"fieldname":"threshold", "label":"Attendance % Below", "fieldtype":"Float", "default": 75, "reqd": 1}
    ]
};
